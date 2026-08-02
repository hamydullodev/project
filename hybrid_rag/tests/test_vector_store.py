"""
Unit tests for app.retriever.vector_store.FAISSVectorStore.

Uses small synthetic random unit vectors (deterministic via a fixed seed)
rather than real embeddings, since this module's correctness doesn't
depend on embedding semantics — only on FAISS index bookkeeping (id
mapping, add/remove/search/save/load) being right.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.retriever.vector_store import FAISSVectorStore, VectorStoreError

DIM = 8


def _unit_vectors(n: int, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vecs = rng.standard_normal((n, DIM)).astype(np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs


@pytest.fixture()
def store() -> FAISSVectorStore:
    return FAISSVectorStore(dimension=DIM)


def test_new_store_is_empty(store: FAISSVectorStore):
    assert len(store) == 0
    assert store.is_empty


def test_add_increases_size(store: FAISSVectorStore):
    ids = [f"doc::{i:03d}" for i in range(5)]
    store.add(ids, _unit_vectors(5))
    assert len(store) == 5
    assert not store.is_empty


def test_add_mismatched_lengths_raises(store: FAISSVectorStore):
    with pytest.raises(ValueError):
        store.add(["a", "b"], _unit_vectors(3))


def test_add_wrong_dimension_raises(store: FAISSVectorStore):
    wrong_dim_vecs = np.random.randn(2, DIM + 1).astype(np.float32)
    with pytest.raises(ValueError):
        store.add(["a", "b"], wrong_dim_vecs)


def test_add_empty_is_noop(store: FAISSVectorStore):
    store.add([], np.empty((0, DIM), dtype=np.float32))
    assert len(store) == 0


def test_search_returns_self_as_top_match(store: FAISSVectorStore):
    ids = [f"doc::{i:03d}" for i in range(6)]
    vecs = _unit_vectors(6)
    store.add(ids, vecs)

    results = store.search(vecs[2], top_k=3)
    assert results[0][0] == ids[2]
    assert results[0][1] == pytest.approx(1.0, abs=1e-4)
    # Scores must be sorted descending.
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


def test_search_on_empty_store_returns_empty_list(store: FAISSVectorStore):
    assert store.search(_unit_vectors(1)[0], top_k=5) == []


def test_search_top_k_larger_than_store_size(store: FAISSVectorStore):
    ids = [f"doc::{i:03d}" for i in range(3)]
    store.add(ids, _unit_vectors(3))

    results = store.search(_unit_vectors(1, seed=99)[0], top_k=100)
    assert len(results) == 3  # capped at actual store size, no padding/-1 entries


def test_add_same_chunk_id_replaces_not_duplicates(store: FAISSVectorStore):
    ids = ["doc::001"]
    v1 = _unit_vectors(1, seed=1)
    store.add(ids, v1)
    assert len(store) == 1

    v2 = _unit_vectors(1, seed=2)  # different vector, same chunk_id
    store.add(ids, v2)
    assert len(store) == 1  # still 1, not 2

    # The stored vector must be the NEW one, not the old one.
    results = store.search(v2[0], top_k=1)
    assert results[0][1] == pytest.approx(1.0, abs=1e-4)


def test_remove_deletes_vector(store: FAISSVectorStore):
    ids = [f"doc::{i:03d}" for i in range(4)]
    vecs = _unit_vectors(4)
    store.add(ids, vecs)

    store.remove([ids[1]])
    assert len(store) == 3

    results = store.search(vecs[1], top_k=4)
    returned_ids = [cid for cid, _ in results]
    assert ids[1] not in returned_ids


def test_remove_unknown_id_is_noop(store: FAISSVectorStore):
    ids = [f"doc::{i:03d}" for i in range(3)]
    store.add(ids, _unit_vectors(3))

    store.remove(["nonexistent::999"])
    assert len(store) == 3


def test_save_and_load_round_trip(store: FAISSVectorStore, tmp_path: Path):
    ids = [f"doc::{i:03d}" for i in range(5)]
    vecs = _unit_vectors(5)
    store.add(ids, vecs)

    index_stem = tmp_path / "test_index"
    store.save(index_stem)

    loaded = FAISSVectorStore.load(index_stem)
    assert len(loaded) == len(store)
    assert loaded.dimension == store.dimension

    results = loaded.search(vecs[3], top_k=1)
    assert results[0][0] == ids[3]


def test_save_creates_expected_files(store: FAISSVectorStore, tmp_path: Path):
    store.add(["doc::001"], _unit_vectors(1))
    index_stem = tmp_path / "my_index"
    store.save(index_stem)

    assert (tmp_path / "my_index.faiss").exists()
    assert (tmp_path / "my_index.meta.json").exists()


def test_load_missing_files_raises_vector_store_error(tmp_path: Path):
    with pytest.raises(VectorStoreError):
        FAISSVectorStore.load(tmp_path / "does_not_exist")


def test_load_corrupted_meta_json_raises_vector_store_error(store: FAISSVectorStore, tmp_path: Path):
    store.add(["doc::001"], _unit_vectors(1))
    index_stem = tmp_path / "index"
    store.save(index_stem)

    # Corrupt the sidecar JSON file.
    meta_path = tmp_path / "index.meta.json"
    meta_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(VectorStoreError):
        FAISSVectorStore.load(index_stem)


def test_load_inconsistent_dimension_raises_vector_store_error(store: FAISSVectorStore, tmp_path: Path):
    import json

    store.add(["doc::001"], _unit_vectors(1))
    index_stem = tmp_path / "index"
    store.save(index_stem)

    meta_path = tmp_path / "index.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["dimension"] = DIM + 1  # deliberately wrong
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(VectorStoreError):
        FAISSVectorStore.load(index_stem)


def test_remove_then_readd_reuses_slot_without_growing_ids(store: FAISSVectorStore):
    """Removing and re-adding under the same chunk_id must not leak
    internal ids unboundedly across many cycles (sanity check that the
    mapping dicts stay bounded to currently-present chunks)."""
    ids = ["doc::001"]
    for i in range(10):
        store.add(ids, _unit_vectors(1, seed=i))
    assert len(store) == 1
    assert len(store._chunk_id_to_int) == 1
    assert len(store._int_to_chunk_id) == 1
