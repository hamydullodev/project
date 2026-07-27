"""
BM25-backed sparse (lexical) index: the "S" in hybrid search.

WHY THIS MODULE EXISTS
-----------------------
FAISS (Milestone 6) finds chunks whose *meaning* is close to a query, even
when the exact wording differs — but that same strength is a weakness for
legal text, where an exact term or article number often matters more than
paraphrased meaning. A query like "261-modda nima haqida?" (What is
article 261 about?) should retrieve the chunk containing "261-modda"
essentially by exact lexical match, something embeddings can blur (an
embedding model has no special notion that "261" is a precise identifier
rather than just a nearby number). BM25 is a classic, well-understood
statistical ranking function built exactly for this: it scores documents
by how often query terms appear in them, weighted by how rare (and
therefore informative) each term is across the whole corpus. Combined with
FAISS in Milestone 8, the two together catch what either alone would
miss — this module builds the "sparse" (lexical/exact-match) half.

HOW BM25 WORKS INTERNALLY (BRIEF)
--------------------------------------
For a query term t and document d, BM25 combines two things:
  - **Term frequency (TF)**: how many times t appears in d, with
    diminishing returns (the 5th occurrence adds much less score than the
    1st) — controlled by the `k1` parameter.
  - **Inverse document frequency (IDF)**: how rare t is across the WHOLE
    corpus — a term appearing in nearly every document (e.g. "qonun",
    "modda" in a legal corpus) contributes little to distinguishing one
    document from another, so its weight is low; a rare term contributes
    more.
  - **Length normalization**: a term match in a short document counts for
    more than the same match in a long one relative to the corpus's
    average document length — controlled by the `b` parameter.
`rank_bm25`'s `BM25Okapi` implements the classic Okapi BM25 variant with
standard defaults (`k1=1.5`, `b=0.75`) — this module uses them as-is
rather than exposing them as tunable settings, since re-tuning BM25
hyperparameters meaningfully requires a labeled relevance-evaluation set
(see Milestone 20's retrieval evaluation), which is out of scope for
getting a working baseline.

WHY BM25 CANNOT BE INCREMENTALLY UPDATED (UNLIKE FAISS)
--------------------------------------------------------------
This is a genuine, important architectural asymmetry between the dense
and sparse halves of this project's hybrid retriever, not an
implementation shortcut: BM25's IDF weights are a statistic over the
ENTIRE corpus (how many of all documents contain each term). Adding one
new document changes the correct IDF value for potentially every term in
the corpus. `rank_bm25` reflects this directly — `BM25Okapi` computes all
its statistics once in `__init__` from the full corpus and has no
`add_document` method. FAISS, by contrast, can add one vector at a time
because a vector's position in space doesn't depend on what other vectors
exist. Consequently, this module's public API has no `add`/`remove`
methods like `FAISSVectorStore` does — only `build`, which always
(re)constructs the index from the full current corpus. The indexing
pipeline (Milestone 10) handles this by always rebuilding the BM25 index
from SQLite's `get_all_chunks()` whenever ANY document changes, not just
the changed one — more expensive per update than FAISS's incremental add,
but correct, and still fast at this corpus's scale (see complexity notes
below).

TIME / MEMORY COMPLEXITY
-------------------------
- `build`: O(total corpus tokens) to tokenize everything, then O(total
  corpus tokens) again for `BM25Okapi` to compute term frequencies and
  IDF — for ~5,000 chunks of a few hundred words each, this is well under
  a second in practice.
- `search`: O(corpus size x average query-term document frequency) —
  `BM25Okapi.get_scores` computes a score for every document in the
  corpus for each query term, which is fast at this corpus's scale
  (thousands, not millions, of chunks) but does NOT scale as well as an
  inverted-index-based BM25 implementation would at much larger scale
  (see Alternatives below).
- Memory: O(total corpus tokens) for the tokenized corpus and BM25's
  internal term-frequency/IDF tables — a few MB for this project's corpus.

ADVANTAGES
-----------
- Exact-term and article-number matching that dense embeddings alone
  reliably miss.
- No training/fitting step beyond tokenizing and counting — fully
  deterministic, no randomness, trivially reproducible.
- Extremely well-understood, decades-old ranking function with predictable
  behavior — useful for an educational project where "why did this rank
  higher" should have a clear, explainable answer.

DISADVANTAGES
--------------
- No incremental updates (see above) — every corpus change requires a
  full rebuild.
- `rank_bm25`'s `BM25Okapi` scores every document in the corpus for every
  query (no inverted index), which is fine at this project's scale but
  would need to be swapped for a production search engine (Elasticsearch,
  Whoosh with an inverted index) at a much larger corpus size.
- No stemming/stopword removal (see `tokenizer.py`'s docstring) — a
  genuine recall limitation for Uzbek's rich morphology.

ALTERNATIVES CONSIDERED
-------------------------
- `Whoosh` or `Elasticsearch`/`OpenSearch` for BM25: production search
  engines with real inverted indexes and incremental update support —
  substantially more infrastructure (a running service, in Elasticsearch's
  case) than a personal, fully-local legal corpus of a few thousand
  chunks needs. `rank_bm25` is a small, pure-Python library that does
  exactly the ranking math needed here with zero extra moving parts.
- Building a custom inverted index by hand: more control, but `rank_bm25`
  already implements the standard, well-tested BM25 formula correctly;
  reimplementing it would be redundant for an already-solved, well-defined
  problem.

BEST PRACTICES APPLIED
------------------------
- The SAME `tokenize()` function (see tokenizer.py) is used at build time
  and query time — see that module's docstring for why any divergence
  here silently breaks matching.
- `save`/`load` follow the same temp-file-then-rename and explicit
  validation pattern as `FAISSVectorStore` (Milestone 6), for the same
  reason: a crash mid-write must not corrupt the persisted index, and a
  corrupted/incompatible file must raise one clear, catchable exception
  type rather than a raw `pickle`/`OSError`.
"""

from __future__ import annotations

import pickle
import tempfile
from pathlib import Path
from typing import Optional

from app.config import settings
from app.retriever.tokenizer import tokenize
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BM25IndexError(Exception):
    """Raised on a corrupted, missing, or inconsistent BM25 index file."""


class BM25SparseIndex:
    """Lexical (term-matching) index over chunk text, built with Okapi BM25."""

    def __init__(self) -> None:
        self._bm25 = None
        self._chunk_ids: list[str] = []

    def __len__(self) -> int:
        return len(self._chunk_ids)

    @property
    def is_empty(self) -> bool:
        return len(self) == 0

    # -- build (always full-corpus; see module docstring for why) ------------------

    def build(self, chunk_ids: list[str], texts: list[str]) -> None:
        """(Re)build the index from the full current corpus.

        There is no `add`/`remove` — BM25's IDF statistics are corpus-
        wide, so any change to the corpus requires recomputing them from
        scratch. Callers (the indexing pipeline, Milestone 10) should
        call this with ALL current chunks, not just newly-added ones.
        """
        if len(chunk_ids) != len(texts):
            raise ValueError(
                f"chunk_ids length ({len(chunk_ids)}) must match texts length ({len(texts)})"
            )

        if not chunk_ids:
            self._bm25 = None
            self._chunk_ids = []
            logger.info("Built empty BM25 index (0 chunks)")
            return

        from rank_bm25 import BM25Okapi

        tokenized_corpus = [tokenize(t) for t in texts]
        self._bm25 = BM25Okapi(tokenized_corpus)
        self._chunk_ids = list(chunk_ids)
        logger.info("Built BM25 index over %d chunk(s)", len(self._chunk_ids))

    # -- search -----------------------------------------------------------------

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """Return up to `top_k` (chunk_id, bm25_score) pairs, best first.

        Unlike FAISS's cosine similarity (bounded to [-1, 1]), BM25 scores
        are unbounded above and — less obviously — CAN be negative: the
        classic Robertson/Sparck-Jones IDF term,
        `log(N - n + 0.5) - log(n + 0.5)`, goes negative for a term
        appearing in more than half the corpus (e.g. "modda" in a legal
        corpus is a realistic example), meaning that term's contribution
        actively penalizes a document's score rather than helping it —
        working as intended (an extremely common term carries little
        distinguishing signal), but a real property to know when
        interpreting raw scores. Milestone 8's hybrid fusion normalizes
        scores before combining dense and sparse results.
        """
        if self.is_empty:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        # argsort ascending, then take the top_k largest — avoids a full
        # O(n log n) sort when top_k is much smaller than the corpus, via
        # numpy's argpartition (O(n)) for the common case.
        import numpy as np

        k = min(top_k, len(scores))
        top_indices = np.argpartition(scores, -k)[-k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        # A non-positive score means this document contributed no genuine
        # positive lexical evidence for the query (either no query term
        # appeared at all, giving exactly 0, or the only matching terms
        # were common enough to have zero/negative IDF - see above).
        # Excluding these keeps the hybrid retriever's candidate pool
        # free of results BM25 itself considers non-evidence, rather than
        # padding it with arbitrary "least-bad" noise just to reach top_k.
        return [
            (self._chunk_ids[i], float(scores[i]))
            for i in top_indices
            if scores[i] > 0
        ]

    # -- persistence --------------------------------------------------------------

    def save(self, path: Optional[Path] = None) -> None:
        """Persist the BM25 index to disk via pickle.

        Writes to a temporary file and renames into place (same rationale
        as `FAISSVectorStore.save`): a crash mid-write leaves the
        previous valid file untouched instead of a half-written,
        corrupted pickle.
        """
        index_path = self._resolve_path(path)
        index_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {"bm25": self._bm25, "chunk_ids": self._chunk_ids}

        with tempfile.NamedTemporaryFile(
            dir=index_path.parent, suffix=".pkl.tmp", delete=False
        ) as tmp_file:
            pickle.dump(payload, tmp_file)
            tmp_path = Path(tmp_file.name)

        tmp_path.replace(index_path)
        logger.info("Saved BM25 index (%d chunks) to %s", len(self), index_path)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "BM25SparseIndex":
        """Load a previously-saved BM25 index from disk.

        Raises `BM25IndexError` (not a raw pickle/OSError) on a missing
        or corrupted file, so callers can catch one exception type and
        trigger a rebuild from SQLite — the spec's "gracefully handle
        corrupted indexes" requirement.
        """
        index_path = cls._resolve_path_static(path)

        if not index_path.exists():
            raise BM25IndexError(f"BM25 index file not found at {index_path}")

        try:
            with index_path.open("rb") as f:
                payload = pickle.load(f)
        except (pickle.UnpicklingError, EOFError, AttributeError, OSError) as e:
            raise BM25IndexError(f"Could not read BM25 index at {index_path}: {e}") from e

        if not isinstance(payload, dict) or "bm25" not in payload or "chunk_ids" not in payload:
            raise BM25IndexError(f"BM25 index file at {index_path} has an unexpected format")

        store = cls.__new__(cls)
        store._bm25 = payload["bm25"]
        store._chunk_ids = payload["chunk_ids"]

        if store._bm25 is not None and len(store._chunk_ids) != len(store._bm25.doc_len):
            raise BM25IndexError(
                f"Chunk id count ({len(store._chunk_ids)}) does not match BM25 "
                f"document count ({len(store._bm25.doc_len)}) — index is inconsistent."
            )

        logger.info("Loaded BM25 index (%d chunks) from %s", len(store), index_path)
        return store

    @staticmethod
    def _resolve_path_static(path: Optional[Path]) -> Path:
        return path or settings.bm25_path_resolved

    def _resolve_path(self, path: Optional[Path]) -> Path:
        return self._resolve_path_static(path)
