"""
Hybrid retrieval: fusing FAISS (dense) and BM25 (sparse) search results.

WHY THIS MODULE EXISTS
-----------------------
Milestones 6 and 7 built two independent ways to find candidate chunks for
a query — semantic similarity (FAISS) and exact lexical overlap (BM25).
Each catches cases the other misses (see their respective module
docstrings), but a RAG pipeline needs ONE ranked list of chunks to pass to
the reranker (Milestone 9), not two separate ones. This module is where
those two lists become one, via weighted score fusion.

WHY SCORES MUST BE NORMALIZED BEFORE COMBINING
------------------------------------------------------
FAISS's cosine similarity lives in [-1, 1] (in practice mostly [0, 1] for
this project's normalized embeddings on real text). BM25's score is
unbounded above and can be negative (see bm25_index.py's docstring on
negative IDF). Averaging a cosine similarity of, say, 0.72 with a BM25
score of 11.4 using fixed weights would let BM25's larger numeric scale
dominate the combination regardless of the configured weights — the
weights would stop meaning what `DENSE_WEIGHT`/`SPARSE_WEIGHT` in `.env`
claim they mean. This module min-max normalizes each modality's scores
to [0, 1] *within that query's own candidate set* before combining, so a
weight of 0.5/0.5 genuinely means "equal influence," independent of each
method's native score scale.

HOW THE FUSION WORKS
--------------------------
1. Retrieve the top `TOP_K` candidates independently from FAISS and from
   BM25 (each may return a different, possibly only partially-overlapping
   set of chunk ids — that's expected and desired, not an error).
2. Min-max normalize each list's raw scores to [0, 1] independently.
3. Take the UNION of chunk ids from both lists. For a chunk present in
   only one modality's results, its other modality's normalized score is
   treated as `0.0` — i.e. "no evidence of relevance from that method,"
   not "missing data to impute." This is a deliberate modeling choice:
   a chunk BM25 didn't even consider a top candidate shouldn't get an
   imputed/interpolated sparse score, it should get the same treatment as
   "no lexical relevance found."
4. `combined_score = dense_weight * dense_normalized + sparse_weight *
   sparse_normalized`, and the union is sorted by this descending.

Every intermediate value (raw dense score, raw sparse score, both
normalized, and the final combined score) is kept on the returned
`HybridSearchResult`, not discarded after computing the final ranking —
this is exactly the data Milestone 18's Retrieval Debug page needs to
show ("dense score, sparse score, final score... metadata") to make the
fusion process inspectable rather than a black box.

TIME / MEMORY COMPLEXITY
-------------------------
- O(TOP_K log TOP_K) for each modality's own internal ranking (already
  paid inside FAISS's/BM25's `search()`), plus O(TOP_K) for normalization
  and O(TOP_K log TOP_K) for the final combined sort — TOP_K is small
  (tens, per `.env`'s default), so this entire fusion step is
  microseconds, negligible next to the embedding/search costs that
  produced the two candidate lists.
- Memory: O(TOP_K) for the union of candidates — never holds the full
  corpus in memory at this stage.

ADVANTAGES
-----------
- Configurable, interpretable weighting (`DENSE_WEIGHT`/`SPARSE_WEIGHT`)
  that behaves as advertised because scores are normalized first.
- Full score transparency for debugging/education — nothing is a
  black-box "trust the fused score."

DISADVANTAGES
--------------
- Min-max normalization is sensitive to outliers: one unusually
  high-scoring candidate compresses every other candidate's normalized
  score toward 0, which can flatten meaningful differences among the
  rest of the list. Acceptable here because the reranker (Milestone 9)
  applies a second, more accurate pass on the fused top candidates
  anyway — this fusion step only needs to get a good candidate SET, not
  a perfectly precise final ranking.
- Normalization is computed per-query, over only that query's retrieved
  candidates — it cannot be precomputed or cached across queries.

ALTERNATIVES CONSIDERED
-------------------------
- **Reciprocal Rank Fusion (RRF)**: combine using only each result's RANK
  (`score = 1 / (k + rank)`) instead of normalized raw scores, entirely
  sidestepping the "scores live on different scales" problem. A
  legitimate, widely-used alternative (e.g. in Elasticsearch's hybrid
  search) — not used here because it discards magnitude information
  (a dense score of 0.95 and 0.51 both retrieved at rank 1 on different
  queries are treated identically by RRF), and because the project's own
  `DENSE_WEIGHT`/`SPARSE_WEIGHT` configuration only makes sense with a
  score-based (not rank-only) combination.
- Training a learned fusion model (e.g. logistic regression over both
  scores against relevance labels): more accurate in principle, but
  requires labeled relevance data this project doesn't have — min-max
  weighted fusion is the standard, dependency-free baseline.

BEST PRACTICES APPLIED
------------------------
- Normalization and fusion logic are pure functions of their inputs
  (`_min_max_normalize`), independently unit-testable without needing a
  loaded FAISS/BM25 index.
- `HybridRetriever` receives its `FAISSVectorStore`/`BM25SparseIndex`/
  `EmbeddingModel` via constructor injection rather than loading them
  itself — retrieval logic doesn't need to know or care whether those
  indexes were just built in-memory (during indexing) or loaded from disk
  (during a query), keeping this module simple and easy to unit test with
  small in-memory indexes.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.config import settings
from app.retriever.bm25_index import BM25SparseIndex
from app.retriever.embeddings import EmbeddingModel
from app.retriever.vector_store import FAISSVectorStore
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HybridSearchResult(BaseModel):
    """One retrieved chunk with full score provenance, for both ranking and debugging.

    Every field here is kept (not just the final combined score) so the
    Retrieval Debug page (Milestone 18) can show exactly how each
    candidate arrived at its final rank.
    """

    chunk_id: str
    dense_score: float | None = None
    sparse_score: float | None = None
    dense_score_normalized: float = 0.0
    sparse_score_normalized: float = 0.0
    combined_score: float = 0.0


def _min_max_normalize(scores: list[float]) -> list[float]:
    """Scale `scores` to [0, 1] via min-max normalization.

    If every score is identical (including the single-element and
    empty-list cases), returns 1.0 for each — with nothing to
    discriminate between candidates, treating them as equally strong
    matches is more honest than an arbitrary tie-break, and avoids a
    division by zero.
    """
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi == lo:
        return [1.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


class HybridRetriever:
    """Combines FAISS dense search and BM25 sparse search into one ranked list."""

    def __init__(
        self,
        vector_store: FAISSVectorStore,
        bm25_index: BM25SparseIndex,
        embedding_model: EmbeddingModel,
        dense_weight: float | None = None,
        sparse_weight: float | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.embedding_model = embedding_model
        self.dense_weight = dense_weight if dense_weight is not None else settings.dense_weight
        self.sparse_weight = sparse_weight if sparse_weight is not None else settings.sparse_weight

    def retrieve(self, query: str, top_k: int | None = None) -> list[HybridSearchResult]:
        """Return chunks ranked by fused dense+sparse relevance to `query`.

        `top_k` controls how many candidates are requested from EACH of
        FAISS and BM25 independently (matching `settings.top_k`'s
        documented meaning) — the returned list's length is the size of
        their UNION, which is between `top_k` (full overlap) and
        `2 * top_k` (no overlap at all), not capped at `top_k` itself.
        Callers that want a hard cap (e.g. before reranking) should slice
        the result themselves.
        """
        top_k = top_k or settings.top_k

        dense_hits: list[tuple[str, float]] = []
        if not self.vector_store.is_empty:
            query_vector = self.embedding_model.embed_query(query)
            dense_hits = self.vector_store.search(query_vector, top_k=top_k)

        sparse_hits: list[tuple[str, float]] = []
        if not self.bm25_index.is_empty:
            sparse_hits = self.bm25_index.search(query, top_k=top_k)

        dense_ids = [cid for cid, _ in dense_hits]
        dense_raw = [score for _, score in dense_hits]
        dense_norm = _min_max_normalize(dense_raw)
        dense_by_id = dict(zip(dense_ids, dense_raw))
        dense_norm_by_id = dict(zip(dense_ids, dense_norm))

        sparse_ids = [cid for cid, _ in sparse_hits]
        sparse_raw = [score for _, score in sparse_hits]
        sparse_norm = _min_max_normalize(sparse_raw)
        sparse_by_id = dict(zip(sparse_ids, sparse_raw))
        sparse_norm_by_id = dict(zip(sparse_ids, sparse_norm))

        all_ids = set(dense_ids) | set(sparse_ids)

        results = []
        for chunk_id in all_ids:
            dense_score_norm = dense_norm_by_id.get(chunk_id, 0.0)
            sparse_score_norm = sparse_norm_by_id.get(chunk_id, 0.0)
            combined = self.dense_weight * dense_score_norm + self.sparse_weight * sparse_score_norm
            results.append(
                HybridSearchResult(
                    chunk_id=chunk_id,
                    dense_score=dense_by_id.get(chunk_id),
                    sparse_score=sparse_by_id.get(chunk_id),
                    dense_score_normalized=dense_score_norm,
                    sparse_score_normalized=sparse_score_norm,
                    combined_score=combined,
                )
            )

        results.sort(key=lambda r: r.combined_score, reverse=True)
        logger.info(
            "Hybrid retrieve: query=%r dense_hits=%d sparse_hits=%d union=%d",
            query,
            len(dense_hits),
            len(sparse_hits),
            len(results),
        )
        return results
