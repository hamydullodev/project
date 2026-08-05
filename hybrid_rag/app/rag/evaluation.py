"""
Retrieval evaluation: Precision@K, Recall@K, MRR, nDCG@K against a small,
hand-verified golden query set.

WHY THIS MODULE EXISTS
-----------------------
Every prior milestone tests that its OWN stage works correctly in
isolation (FAISS returns the vectors it was given, BM25 tokenizes
consistently, fusion combines scores the way the formula says it should).
None of that answers the question a RAG system's designer actually cares
about: for a REAL question a user might ask, does hybrid retrieval +
reranking together surface the ARTICLE THAT ACTUALLY ANSWERS IT, near the
top of the list? This module answers that with the four standard
information-retrieval metrics the spec names, computed against a small
golden query set built from this project's own real corpus (see
`tests/evaluation/golden_dataset.py`) rather than synthetic data — a
synthetic query risks not resembling what this system will actually be
asked, in Uzbek, about these specific five legal codes.

WHY RELEVANCE IS DEFINED AT THE (law_name, article_number) LEVEL, NOT chunk_id
-------------------------------------------------------------------------------------
A single legal article can be split across multiple chunks (the chunker,
Milestone 4, splits long articles at `CHUNK_SIZE`), and which exact
chunk_id ends up holding "the" answer is an implementation detail of
chunking parameters that can change between runs (a different
`CHUNK_SIZE`, a corpus re-index). Grading against "did this ARTICLE get
found," not "did this exact CHUNK get found," is the definition that
actually tracks answer quality and stays stable across those details.

WHY THESE FUNCTIONS ARE HAND-IMPLEMENTED RATHER THAN CALLING
`sklearn.metrics.ndcg_score` DIRECTLY
------------------------------------------------------------------------
Consistent with this project's general approach (see e.g.
`app/retriever/embeddings.py`'s docstring on using `sentence-transformers`
directly instead of a LangChain wrapper): for an educational project,
seeing exactly how DCG/nDCG/MRR are computed, in plain Python over a list
of booleans, is worth more than a correct-but-opaque library call.
`tests/evaluation/test_retrieval_metrics.py` cross-checks this module's
`ndcg_at_k` against `sklearn.metrics.ndcg_score` on the same inputs, to
confirm the hand-rolled version isn't just plausible-looking but
numerically correct — scikit-learn (already a dependency, added all the
way back in Milestone 1's `requirements.txt` for exactly this purpose) is
used as the trusted reference in that one test, not in the production
code path.

METRIC DEFINITIONS (BRIEF)
---------------------------
Given a ranked list of `k` retrieved items and a set of "relevant" items:
  - **Precision@K**: what fraction of the top K retrieved items are
    relevant. Answers "how much of what came back is actually useful?"
  - **Recall@K**: what fraction of ALL relevant items were found in the
    top K. Answers "of everything worth finding, how much did I find?"
    (This project's golden set has exactly one relevant article per
    query, so Recall@K collapses to 0.0/1.0 here — still computed
    generally, so a future golden query with several correct articles
    works without any code change.)
  - **MRR (Mean Reciprocal Rank)**: the reciprocal of the rank of the
    FIRST relevant result (1/rank, or 0 if none in the top K), averaged
    across queries. Rewards a relevant result landing near the very top,
    not just appearing somewhere in the list.
  - **nDCG@K (normalized Discounted Cumulative Gain)**: like Precision@K,
    but a relevant result at rank 1 counts more than the same result at
    rank 5 (discounted by `log2(rank + 1)`), then normalized against the
    best possible ordering (all relevant items first) so the score always
    lands in [0, 1] regardless of how many relevant items exist.

TIME / MEMORY COMPLEXITY
-------------------------
O(k) per query for every metric — one pass over the top-k relevance
flags, plus a fixed-size ideal ordering for nDCG's normalizer — negligible
next to the retrieval/reranking work that produced the ranked list.

ALTERNATIVES CONSIDERED
-------------------------
See `tests/evaluation/golden_dataset.py`'s docstring for the trade-offs of
an 8-query, hand-curated golden set specifically (small, but every entry
independently verified against the real source text with `grep` while
building it, not guessed).
"""

from __future__ import annotations

import math

from pydantic import BaseModel

from app.config import settings
from app.database import MetadataRepository
from app.reranker import RerankedResult, RerankerModel
from app.retriever import HybridRetriever
from app.utils.logger import get_logger

logger = get_logger(__name__)

RelevanceKey = tuple[str, str]  # (law_name, article_number)


class GoldenQuery(BaseModel):
    """One hand-verified (query -> relevant article) test case.

    `relevant` is a LIST of (law_name, article_number) pairs, not a single
    pair, so a query with more than one acceptable correct answer can be
    expressed without special-casing — see `golden_dataset.py` for why
    this matters for the two procedure codes' near-identical provisions.
    """

    query: str
    relevant: list[RelevanceKey]
    note: str = ""


class QueryMetrics(BaseModel):
    """Precision/Recall/RR/nDCG for one query, plus enough raw data to debug a low score."""

    query: str
    k: int
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float
    hit_rank: int | None = None  # 1-indexed rank of the first relevant result, if any


# -- pure metric functions (operate on plain relevance-flag lists) ------------------


def precision_at_k(relevance_flags: list[bool], k: int) -> float:
    """Fraction of the top `k` results that are relevant."""
    top_k = relevance_flags[:k]
    if not top_k:
        return 0.0
    return sum(top_k) / len(top_k)


def recall_at_k(relevance_flags: list[bool], k: int, total_relevant: int) -> float:
    """Fraction of all relevant items that appear in the top `k` results."""
    if total_relevant == 0:
        return 0.0
    return sum(relevance_flags[:k]) / total_relevant


def reciprocal_rank(relevance_flags: list[bool]) -> float:
    """1/rank of the first relevant result (1-indexed), or 0.0 if none found."""
    for i, is_relevant in enumerate(relevance_flags, start=1):
        if is_relevant:
            return 1.0 / i
    return 0.0


def _dcg_at_k(relevance_flags: list[bool], k: int) -> float:
    """Discounted Cumulative Gain: binary relevance, discounted by log2(rank + 1)."""
    return sum(
        1.0 / math.log2(i + 1) for i, is_relevant in enumerate(relevance_flags[:k], start=1) if is_relevant
    )


def ndcg_at_k(relevance_flags: list[bool], k: int, total_relevant: int) -> float:
    """DCG@K normalized against the best possible ordering (IDCG@K).

    With binary relevance, the ideal ordering places every relevant item
    first, so IDCG@K is just the DCG of `min(total_relevant, k)` leading
    "relevant" flags. Returns 0.0 (not a division-by-zero error) when
    there is nothing relevant to find in the first place.
    """
    ideal_flags = [True] * min(total_relevant, k) + [False] * max(0, k - total_relevant)
    idcg = _dcg_at_k(ideal_flags, k)
    if idcg == 0.0:
        return 0.0
    return _dcg_at_k(relevance_flags, k) / idcg


# -- running the golden set against the real retrieval + reranking pipeline --------


def _relevance_flags(reranked: list[RerankedResult], relevant: set[RelevanceKey]) -> list[bool]:
    return [(r.law_name, r.article_number) in relevant for r in reranked]


def evaluate_query(
    retriever: HybridRetriever,
    reranker: RerankerModel,
    repo: MetadataRepository,
    golden: GoldenQuery,
    k: int | None = None,
) -> QueryMetrics:
    """Run one golden query through hybrid retrieval + reranking and score the result.

    Deliberately stops at reranking — no LLM call, no `RAGPipeline`/Ollama
    dependency. Retrieval quality is a property of retrieval; forcing an
    evaluation run to depend on a running Ollama server (and pay
    generation latency) for a metric that has nothing to do with
    generation would make this harder to run in more environments (e.g.
    CI) for no benefit — the same reasoning `retrieval_debug.py` documents
    for calling `.retrieve()` rather than `.ask()`, just resolved the
    other way here since this module has no UI reason to reuse the
    cached, Ollama-requiring `RAGPipeline`.
    """
    k = k or settings.rerank_top_k
    relevant = set(golden.relevant)

    hybrid_results = retriever.retrieve(golden.query, top_k=settings.top_k)
    chunk_ids = [r.chunk_id for r in hybrid_results]
    chunks_by_id = {c.id: c for c in repo.get_chunks_by_ids(chunk_ids)}
    reranked = reranker.rerank(golden.query, hybrid_results, chunks_by_id, top_k=k)

    flags = _relevance_flags(reranked, relevant)
    hit_rank = next((i for i, is_relevant in enumerate(flags, start=1) if is_relevant), None)

    return QueryMetrics(
        query=golden.query,
        k=k,
        precision_at_k=precision_at_k(flags, k),
        recall_at_k=recall_at_k(flags, k, total_relevant=len(relevant)),
        reciprocal_rank=reciprocal_rank(flags),
        ndcg_at_k=ndcg_at_k(flags, k, total_relevant=len(relevant)),
        hit_rank=hit_rank,
    )


def evaluate_dataset(
    retriever: HybridRetriever,
    reranker: RerankerModel,
    repo: MetadataRepository,
    golden_queries: list[GoldenQuery],
    k: int | None = None,
) -> list[QueryMetrics]:
    """Evaluate every golden query, logging each result as it's computed."""
    results = []
    for golden in golden_queries:
        metrics = evaluate_query(retriever, reranker, repo, golden, k=k)
        logger.info(
            "Eval query=%r P@%d=%.2f R@%d=%.2f RR=%.2f nDCG@%d=%.2f hit_rank=%s",
            metrics.query,
            metrics.k,
            metrics.precision_at_k,
            metrics.k,
            metrics.recall_at_k,
            metrics.reciprocal_rank,
            metrics.k,
            metrics.ndcg_at_k,
            metrics.hit_rank,
        )
        results.append(metrics)
    return results


def mean_metrics(results: list[QueryMetrics]) -> dict[str, float]:
    """Aggregate mean of each metric across all queries — the headline numbers."""
    if not results:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0, "mrr": 0.0, "ndcg_at_k": 0.0}
    n = len(results)
    return {
        "precision_at_k": sum(r.precision_at_k for r in results) / n,
        "recall_at_k": sum(r.recall_at_k for r in results) / n,
        "mrr": sum(r.reciprocal_rank for r in results) / n,
        "ndcg_at_k": sum(r.ndcg_at_k for r in results) / n,
    }
