"""
Retrieval quality regression test: runs the golden query set (Milestone
20) through the REAL hybrid retriever + reranker over this project's
actual indexed corpus, and asserts the aggregate metrics stay above a
floor.

WHY THIS RUNS AGAINST THE REAL PROJECT INDEX, NOT AN ISOLATED TEST FIXTURE
--------------------------------------------------------------------------------
Every golden query in `golden_dataset.py` was verified against the real
`documents/raw/*.txt` source text — the question this test asks is "does
retrieval actually work well on the real corpus this project ships with,"
which is only answerable by querying that real corpus. This mirrors
`test_chat_page.py`'s and `test_retrieval_debug_page.py`'s established
precedent (see their own docstrings) of testing against the real,
already-indexed project data rather than building a synthetic fixture —
the real corpus is legitimate, representative state, not test pollution.
Nothing here mutates the index (only `.retrieve()`-equivalent reads), so
running this test is safe to do at any time without disturbing it.

WHY THE THRESHOLDS ARE LOOSE (NOT "must be 1.0")
------------------------------------------------------
This is a REGRESSION guard, not a claim that retrieval is perfect. Eight
queries is too small a sample for a tight threshold to be meaningful
(missing even one query moves the mean by 12.5 percentage points), and
some slack is deliberately left for legitimate retrieval behavior a
tighter bound would incorrectly fail on (e.g. a near-duplicate provision
in a neighboring article scoring competitively). The specific values
below were set by running this exact test against the real corpus during
this milestone and leaving comfortable headroom under the observed
scores — if a future change to chunking, the embedding model, or fusion
weights drops scores meaningfully below where they are today, that's
exactly the regression this test exists to catch.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.database import MetadataRepository
from app.rag.evaluation import evaluate_dataset, mean_metrics
from app.reranker import RerankerModel
from app.retriever import (
    BM25IndexError,
    BM25SparseIndex,
    FAISSVectorStore,
    HybridRetriever,
    VectorStoreError,
    get_default_embedding_model,
)
from tests.evaluation.golden_dataset import GOLDEN_QUERIES

# This project's real corpus (5 codes, ~4,400 chunks) must actually be
# indexed for this test to be meaningful - skip cleanly rather than fail
# confusingly on a fresh checkout before anyone has run indexing yet.
_repo_probe = MetadataRepository()
pytestmark = pytest.mark.skipif(
    _repo_probe.get_statistics()["total_chunks"] == 0,
    reason="No indexed corpus found - run Index management's 'Qurish / yangilash' first.",
)


@pytest.fixture(scope="module")
def retrieval_stack():
    """Real embedding model + real FAISS/BM25 indexes + real reranker, loaded once.

    Module-scoped: every test in this file reuses the same loaded models
    (each a real, multi-second cost - see Milestones 5 and 9) rather than
    reloading per test, the same rationale `st.cache_resource` uses in the
    UI (`app/ui/resources.py`).
    """
    embedding_model = get_default_embedding_model()

    try:
        vector_store = FAISSVectorStore.load()
    except VectorStoreError:
        vector_store = FAISSVectorStore(dimension=embedding_model.dimension)

    try:
        bm25_index = BM25SparseIndex.load()
    except BM25IndexError:
        bm25_index = BM25SparseIndex()

    retriever = HybridRetriever(vector_store, bm25_index, embedding_model)
    reranker = RerankerModel()
    repo = MetadataRepository()
    return retriever, reranker, repo


def test_golden_dataset_is_internally_consistent():
    """Sanity-check the dataset itself before trusting scores computed from it."""
    assert len(GOLDEN_QUERIES) == 8
    for golden in GOLDEN_QUERIES:
        assert golden.query.strip()
        assert len(golden.relevant) >= 1
        for law_name, article_number in golden.relevant:
            assert law_name.strip()
            assert article_number.strip()


def test_every_golden_article_actually_exists_in_the_indexed_corpus(retrieval_stack):
    """Catches a stale golden entry (e.g. after a corpus re-index changes article parsing)."""
    _, _, repo = retrieval_stack
    all_chunks = repo.get_all_chunks()
    indexed_pairs = {(c.law_name, c.article_number) for c in all_chunks}

    for golden in GOLDEN_QUERIES:
        for relevant_pair in golden.relevant:
            assert relevant_pair in indexed_pairs, (
                f"Golden query {golden.query!r} expects {relevant_pair}, "
                f"which is not present in the indexed corpus."
            )


def test_retrieval_quality_meets_floor(retrieval_stack):
    retriever, reranker, repo = retrieval_stack
    results = evaluate_dataset(retriever, reranker, repo, GOLDEN_QUERIES, k=settings.rerank_top_k)
    aggregate = mean_metrics(results)

    failures = [r for r in results if r.hit_rank is None]
    failure_detail = "; ".join(f"{r.query!r}" for r in failures)

    assert aggregate["mrr"] >= 0.5, (
        f"Mean Reciprocal Rank dropped below floor (got {aggregate['mrr']:.2f}). "
        f"Queries with no hit in top-{settings.rerank_top_k}: {failure_detail or 'none'}"
    )
    assert aggregate["ndcg_at_k"] >= 0.5, f"nDCG@{settings.rerank_top_k} dropped below floor: {aggregate}"
    assert aggregate["precision_at_k"] >= 0.15, f"Precision@{settings.rerank_top_k} dropped below floor: {aggregate}"

    # Every query should at least find its answer SOMEWHERE in the wider
    # (pre-rerank_top_k) candidate pool, even on a run where reranking
    # doesn't push it into the final top-k - a total miss here would mean
    # hybrid retrieval itself, not just reranking, failed to surface the
    # right article at all.
    wide_results = evaluate_dataset(retriever, reranker, repo, GOLDEN_QUERIES, k=settings.top_k)
    total_misses = [r for r in wide_results if r.hit_rank is None]
    assert not total_misses, (
        f"{len(total_misses)} golden quer(y/ies) found NO relevant article even in the "
        f"full top-{settings.top_k} candidate pool: {[r.query for r in total_misses]}"
    )
