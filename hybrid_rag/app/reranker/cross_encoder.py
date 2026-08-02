"""
Cross-encoder reranking: a second, more accurate relevance pass over
the hybrid retriever's top candidates.

WHY THIS MODULE EXISTS
-----------------------
`HybridRetriever` (Milestone 8) is fast because it's built entirely on
*bi-encoders*: the embedding model (Milestone 5) encodes the query and
every chunk SEPARATELY, so all chunk vectors can be precomputed once at
indexing time and compared to a query vector via simple dot products.
That speed comes at a real accuracy cost — a bi-encoder never lets the
query and a specific chunk's tokens directly attend to each other, so it
can miss relevance signals that only become visible when the two texts
are read together.

A *cross-encoder* fixes that: it takes the (query, chunk_text) pair
CONCATENATED as one input to a single transformer, so every query token
can attend to every chunk token (and vice versa) through the model's
self-attention layers, producing a far more accurate relevance judgment.
The catch is cost — nothing about a cross-encoder score can be
precomputed, since it depends on both texts together; scoring the entire
corpus this way would be far too slow for interactive use. This is why
production RAG systems universally use a two-stage design: a cheap
bi-encoder (+ BM25 here) to narrow thousands of chunks down to a small
candidate set (`TOP_K`, e.g. 20), then a cross-encoder to precisely
re-rank just those few candidates down to the small number
(`RERANK_TOP_K`, e.g. 5) actually sent to the LLM. This module is that
second stage.

WHY SIGMOID IS APPLIED TO THE RAW MODEL OUTPUT
------------------------------------------------------
`cross-encoder/ms-marco-MiniLM-L-6-v2` (this project's default reranker)
is a binary relevance classifier trained with `BCEWithLogitsLoss`,
meaning its raw output is an unbounded logit, not a probability —
verified empirically while building this module (a clearly relevant pair
scored logit ≈ +5.4, a clearly irrelevant pair scored logit ≈ -4.7).
Applying `sigmoid` maps these logits to a [0, 1] relevance probability,
giving a score with the same intuitive range and "higher = more
relevant" semantics as the normalized scores already used elsewhere in
this pipeline (FAISS cosine similarity, hybrid fusion scores).

TIME / MEMORY COMPLEXITY
-------------------------
- O(k) forward passes for k candidates (one per query-chunk pair), each
  itself O(L²) in combined sequence length L (self-attention is quadratic
  in sequence length) — meaningfully more expensive per item than a
  bi-encoder's O(L) encoding, which is exactly why this only ever runs on
  `TOP_K` candidates (tens), never the full corpus (thousands).
- Memory: O(k · L) for the batch of tokenized pairs held during
  inference — negligible at this candidate-set size.

ADVANTAGES
-----------
- Substantially more accurate relevance judgments than bi-encoder cosine
  similarity alone, because the model can directly compare specific
  phrases across the query and chunk rather than comparing two
  independently-compressed vectors.
- Applied only to a small candidate set, so the accuracy gain is nearly
  free in wall-clock terms relative to the LLM generation step that
  follows it.

DISADVANTAGES
--------------
- Cannot be precomputed or cached across queries — a genuine per-query
  cost, unlike the FAISS/BM25 indexes built once at ingestion time.
- Truncates long chunk text to the model's max sequence length (this
  model: 512 tokens for the combined query+passage) — a chunk near
  `CHUNK_SIZE`'s upper bound plus a longer query could lose trailing
  content to truncation; not a concern at this project's default chunk
  size, but worth knowing if `CHUNK_SIZE` is increased substantially.

ALTERNATIVES CONSIDERED
-------------------------
- `BAAI/bge-reranker-large` (mentioned in the original spec as an
  alternative): a larger, generally more accurate multilingual
  cross-encoder; not the default here purely for size/speed (this
  project favors a fast default given the RAM constraints already
  documented for the embedding model — see embeddings.py), but fully
  supported by setting `RERANKER_MODEL` in `.env`, since this module
  makes no model-specific assumptions beyond "a HuggingFace sequence-
  classification cross-encoder that outputs one relevance logit."
- Skipping reranking entirely and using the hybrid fusion score as final
  ranking: simpler and faster, but gives up the accuracy improvement that
  is the entire reason a reranking stage exists in a well-designed RAG
  pipeline.

KNOWN ISSUE: THIS RERANKER MODEL CRASHES ON CPU ON THIS DEV MACHINE
---------------------------------------------------------------------------
While building this module, running `cross-encoder/ms-marco-MiniLM-L-6-v2`
on `device="cpu"` reliably crashed with SIGBUS (exit code 138) during the
model's forward pass — reproduced identically via the `sentence-
transformers` `CrossEncoder` wrapper AND via raw `transformers`
(`AutoModelForSequenceClassification`), with and without
`token_type_ids`, and with threading forced to 1 — ruling out the
OpenMP/threading conflict documented in `app/__init__.py` (Milestone 6)
as the cause. Running the identical model on `device="mps"` instead
worked correctly and reliably (confirmed relevant/irrelevant pairs scored
+5.4/-4.7 as expected). This looks like a deeper incompatibility between
this specific BERT-architecture forward pass, this machine's PyTorch
build (`2.13.0`, linked against Apple's Accelerate BLAS), and CPU
execution specifically — not something fixable at the Python level here.
Since `RERANKER_DEVICE=auto` (the default) already resolves to `mps` on
any Mac with Apple Silicon (via `app.utils.device.resolve_device`), this
does not require any special handling by users on similar hardware — but
if you explicitly force `RERANKER_DEVICE=cpu` on a Mac and hit a crash,
this is why; switch to `mps` or leave it as `auto`.

BEST PRACTICES APPLIED
------------------------
- The model instance is cached per (model_name, device) via
  `functools.lru_cache`, mirroring `embeddings.py`'s pattern, so repeated
  `RerankerModel(...)` construction reuses already-loaded weights.
- A candidate whose chunk data can't be found (defensive — should not
  happen if the caller populates `chunks` from the same candidate list)
  is logged and skipped rather than crashing the whole rerank call.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from app.config import settings
from app.database.models import ChunkRecord
from app.retriever.hybrid_retriever import HybridSearchResult
from app.utils.device import resolve_device
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RerankedResult(HybridSearchResult):
    """A hybrid search result augmented with its full chunk data and cross-encoder score.

    Extends `HybridSearchResult` (rather than duplicating its fields) so
    every score computed along the way — dense, sparse, combined, and now
    reranker — survives to the Retrieval Debug page (Milestone 18)
    without any information being discarded at this stage.

    The citation fields (`law_name`, `article_number`, `section`,
    `page_number`) are copied from the `ChunkRecord` passed into
    `rerank()` — `HybridRetriever` only ever sees bare chunk ids (Milestone
    8), so this is the first point in the pipeline where a result carries
    the metadata the prompt builder (Milestone 12) needs to construct a
    correct citation.
    """

    text: str
    law_name: str | None = None
    collection_id: str | None = None
    collection_category: str | None = None
    collection_title: str | None = None
    article_number: str | None = None
    section: str | None = None
    page_number: int | None = None
    reranker_score: float = 0.0


@lru_cache(maxsize=2)
def _load_cross_encoder(model_name: str, device: str):
    """Load (and process-wide cache) a CrossEncoder by (name, device).

    See `embeddings.py`'s `_load_sentence_transformer` for the identical
    rationale — avoids reloading model weights across repeated
    `RerankerModel(...)` construction.
    """
    from sentence_transformers import CrossEncoder

    logger.info("Loading reranker model '%s' on device='%s' ...", model_name, device)
    model = CrossEncoder(model_name, device=device)
    logger.info("Loaded reranker model '%s'", model_name)
    return model


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


class RerankerModel:
    """Reranks hybrid retrieval candidates using a cross-encoder."""

    def __init__(self, model_name: str | None = None, device: str | None = None) -> None:
        self.model_name = model_name or settings.reranker_model
        self.device = resolve_device(device or settings.reranker_device)
        self._model = _load_cross_encoder(self.model_name, self.device)

    def rerank(
        self,
        query: str,
        candidates: list[HybridSearchResult],
        chunks: dict[str, ChunkRecord],
        top_k: int | None = None,
    ) -> list[RerankedResult]:
        """Rerank `candidates` by cross-encoder relevance to `query`.

        `chunks` maps chunk_id -> `ChunkRecord`; the caller (the RAG
        pipeline, Milestone 14) is expected to have already hydrated the
        hybrid retriever's chunk ids via
        `MetadataRepository.get_chunks_by_ids()`. Returns the top `top_k`
        candidates sorted by `reranker_score` descending, each carrying
        its source `ChunkRecord`'s citation metadata.
        """
        top_k = top_k if top_k is not None else settings.rerank_top_k

        if not candidates:
            return []

        pairs: list[tuple[str, str]] = []
        valid_candidates: list[HybridSearchResult] = []
        for candidate in candidates:
            chunk = chunks.get(candidate.chunk_id)
            if chunk is None:
                logger.warning(
                    "No chunk data found for chunk_id=%s; skipping in reranking", candidate.chunk_id
                )
                continue
            pairs.append((query, chunk.text))
            valid_candidates.append(candidate)

        if not pairs:
            return []

        raw_scores = self._model.predict(pairs, convert_to_numpy=True)
        scores = _sigmoid(np.asarray(raw_scores))

        reranked = [
            RerankedResult(
                **candidate.model_dump(),
                text=chunks[candidate.chunk_id].text,
                law_name=chunks[candidate.chunk_id].law_name,
                collection_id=chunks[candidate.chunk_id].collection_id,
                collection_category=chunks[candidate.chunk_id].collection_category,
                collection_title=chunks[candidate.chunk_id].collection_title,
                article_number=chunks[candidate.chunk_id].article_number,
                section=chunks[candidate.chunk_id].section,
                page_number=chunks[candidate.chunk_id].page_number,
                reranker_score=float(score),
            )
            for candidate, score in zip(valid_candidates, scores)
        ]
        reranked.sort(key=lambda r: r.reranker_score, reverse=True)

        logger.info(
            "Reranked %d candidate(s) for query=%r, returning top %d",
            len(reranked),
            query,
            min(top_k, len(reranked)),
        )
        return reranked[:top_k]
