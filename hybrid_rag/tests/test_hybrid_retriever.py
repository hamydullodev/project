"""
Unit tests for app.retriever.hybrid_retriever.

Uses small synthetic FAISS/BM25 indexes and a lightweight fake embedding
model (not a real sentence-transformers model) so these tests run fast
and only exercise fusion logic, not embedding quality.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.retriever.bm25_index import BM25SparseIndex
from app.retriever.hybrid_retriever import HybridRetriever, _min_max_normalize
from app.retriever.vector_store import FAISSVectorStore

DIM = 4


class FakeEmbeddingModel:
    """Duck-typed stand-in for EmbeddingModel: only `embed_query` is used
    by HybridRetriever, so only that needs implementing. Returns a fixed,
    caller-configured vector regardless of the query text, so tests can
    control exactly which FAISS candidates come back."""

    def __init__(self, query_vector: np.ndarray) -> None:
        self._query_vector = query_vector

    def embed_query(self, text: str) -> np.ndarray:
        return self._query_vector


# ---------------------------------------------------------------------------
# _min_max_normalize
# ---------------------------------------------------------------------------


def test_min_max_normalize_empty_list():
    assert _min_max_normalize([]) == []


def test_min_max_normalize_single_value():
    assert _min_max_normalize([5.0]) == [1.0]


def test_min_max_normalize_all_equal_values():
    assert _min_max_normalize([3.0, 3.0, 3.0]) == [1.0, 1.0, 1.0]


def test_min_max_normalize_normal_range():
    result = _min_max_normalize([0.0, 5.0, 10.0])
    assert result == [0.0, 0.5, 1.0]


def test_min_max_normalize_negative_values():
    result = _min_max_normalize([-10.0, 0.0, 10.0])
    assert result == [0.0, 0.5, 1.0]


# ---------------------------------------------------------------------------
# HybridRetriever
# ---------------------------------------------------------------------------


def _unit_vector(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(DIM).astype(np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture()
def built_indexes():
    """Build small, overlapping-but-not-identical dense and sparse indexes.

    Dense index: chunks c1..c4, each with a distinct random unit vector.
    Sparse index: chunks c2..c5 plus 4 unrelated padding documents (note:
    c1 is dense-only, c5 is sparse-only, c2-c4 are in both). The query
    terms ("fuqarolik", "huquqi") are made to appear in only 2 of the 8
    sparse documents (c3, c5) deliberately - not in exactly half - to
    avoid the BM25 edge case (documented in bm25_index.py and hit while
    building Milestone 7's tests) where a term appearing in exactly half
    a small corpus gets an IDF of precisely zero and is filtered out of
    results entirely.
    """
    vector_store = FAISSVectorStore(dimension=DIM)
    dense_ids = ["c1", "c2", "c3", "c4"]
    dense_vecs = np.stack([_unit_vector(i) for i in range(4)])
    vector_store.add(dense_ids, dense_vecs)

    bm25_index = BM25SparseIndex()
    sparse_ids = ["c2", "c3", "c4", "c5", "pad1", "pad2", "pad3", "pad4"]
    sparse_texts = [
        "boshqa mavzu haqida qisqa matn",
        "fuqarolik huquqi toʻgʻrisida qoida",
        "yana boshqa narsa haqida gap",
        "fuqarolik huquqi masalasi koʻrib chiqildi",
        "pad matni bir",
        "pad matni ikki",
        "pad matni uch",
        "pad matni toʻrt",
    ]
    bm25_index.build(sparse_ids, sparse_texts)

    return vector_store, bm25_index, dense_vecs


def test_retrieve_combines_both_modalities(built_indexes):
    vector_store, bm25_index, dense_vecs = built_indexes
    # Query vector identical to c1's vector -> c1 should be a strong dense hit.
    fake_embedder = FakeEmbeddingModel(query_vector=dense_vecs[0])
    retriever = HybridRetriever(vector_store, bm25_index, fake_embedder)

    results = retriever.retrieve("fuqarolik huquqi", top_k=10)
    result_ids = {r.chunk_id for r in results}

    # Union of dense {c1,c2,c3,c4} and sparse {c2,c3,c4,c5} = all 5.
    assert result_ids == {"c1", "c2", "c3", "c4", "c5"}


def test_dense_only_chunk_has_zero_sparse_score(built_indexes):
    vector_store, bm25_index, dense_vecs = built_indexes
    fake_embedder = FakeEmbeddingModel(query_vector=dense_vecs[0])
    retriever = HybridRetriever(vector_store, bm25_index, fake_embedder)

    results = {r.chunk_id: r for r in retriever.retrieve("fuqarolik huquqi", top_k=10)}

    c1 = results["c1"]
    assert c1.dense_score is not None
    assert c1.sparse_score is None
    assert c1.sparse_score_normalized == 0.0


def test_sparse_only_chunk_has_zero_dense_score(built_indexes):
    vector_store, bm25_index, dense_vecs = built_indexes
    fake_embedder = FakeEmbeddingModel(query_vector=dense_vecs[0])
    retriever = HybridRetriever(vector_store, bm25_index, fake_embedder)

    results = {r.chunk_id: r for r in retriever.retrieve("fuqarolik huquqi", top_k=10)}

    c5 = results["c5"]
    assert c5.sparse_score is not None
    assert c5.dense_score is None
    assert c5.dense_score_normalized == 0.0


def test_results_sorted_by_combined_score_descending(built_indexes):
    vector_store, bm25_index, dense_vecs = built_indexes
    fake_embedder = FakeEmbeddingModel(query_vector=dense_vecs[0])
    retriever = HybridRetriever(vector_store, bm25_index, fake_embedder)

    results = retriever.retrieve("fuqarolik huquqi", top_k=10)
    scores = [r.combined_score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_dense_weight_one_ignores_sparse_score(built_indexes):
    vector_store, bm25_index, dense_vecs = built_indexes
    fake_embedder = FakeEmbeddingModel(query_vector=dense_vecs[0])
    retriever = HybridRetriever(vector_store, bm25_index, fake_embedder, dense_weight=1.0, sparse_weight=0.0)

    results = {r.chunk_id: r for r in retriever.retrieve("fuqarolik huquqi", top_k=10)}
    for r in results.values():
        assert r.combined_score == pytest.approx(r.dense_score_normalized)

    # c5 (sparse-only) must score 0 combined, since dense_weight=1 and it
    # has no dense presence.
    assert results["c5"].combined_score == 0.0


def test_sparse_weight_one_ignores_dense_score(built_indexes):
    vector_store, bm25_index, dense_vecs = built_indexes
    fake_embedder = FakeEmbeddingModel(query_vector=dense_vecs[0])
    retriever = HybridRetriever(vector_store, bm25_index, fake_embedder, dense_weight=0.0, sparse_weight=1.0)

    results = {r.chunk_id: r for r in retriever.retrieve("fuqarolik huquqi", top_k=10)}
    for r in results.values():
        assert r.combined_score == pytest.approx(r.sparse_score_normalized)

    assert results["c1"].combined_score == 0.0


def test_retrieve_with_empty_bm25_index_uses_dense_only():
    vector_store = FAISSVectorStore(dimension=DIM)
    vecs = np.stack([_unit_vector(i) for i in range(3)])
    vector_store.add(["a", "b", "c"], vecs)

    empty_bm25 = BM25SparseIndex()
    fake_embedder = FakeEmbeddingModel(query_vector=vecs[0])
    retriever = HybridRetriever(vector_store, empty_bm25, fake_embedder)

    results = retriever.retrieve("anything", top_k=5)
    assert len(results) == 3
    assert all(r.sparse_score is None for r in results)


def test_retrieve_with_empty_vector_store_uses_sparse_only():
    empty_store = FAISSVectorStore(dimension=DIM)
    bm25_index = BM25SparseIndex()
    # "fuqarolik huquqi" appears in 1 of 3 documents (a clear minority,
    # not exactly half) so it gets a clearly positive BM25 IDF - see the
    # built_indexes fixture's docstring for why this matters.
    bm25_index.build(
        ["a", "b", "c"],
        ["fuqarolik huquqi", "mehnat shartnomasi", "boshqa mavzu"],
    )

    fake_embedder = FakeEmbeddingModel(query_vector=_unit_vector(0))
    retriever = HybridRetriever(empty_store, bm25_index, fake_embedder)

    results = retriever.retrieve("fuqarolik huquqi", top_k=5)
    assert len(results) >= 1
    assert all(r.dense_score is None for r in results)


def test_retrieve_both_empty_returns_empty_list():
    empty_store = FAISSVectorStore(dimension=DIM)
    empty_bm25 = BM25SparseIndex()
    fake_embedder = FakeEmbeddingModel(query_vector=_unit_vector(0))
    retriever = HybridRetriever(empty_store, empty_bm25, fake_embedder)

    assert retriever.retrieve("anything", top_k=5) == []


def test_default_weights_come_from_settings(built_indexes):
    from app.config import settings

    vector_store, bm25_index, dense_vecs = built_indexes
    fake_embedder = FakeEmbeddingModel(query_vector=dense_vecs[0])
    retriever = HybridRetriever(vector_store, bm25_index, fake_embedder)

    assert retriever.dense_weight == settings.dense_weight
    assert retriever.sparse_weight == settings.sparse_weight
