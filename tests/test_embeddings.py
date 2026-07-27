"""
Unit tests for app.retriever.embeddings.

Explicitly pins the SMALL multilingual model
(sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, ~470MB) —
which also happens to be this project's configured default — rather than
relying on whatever `EMBEDDING_MODEL` a user's `.env` might be set to
(e.g. the heavier `BAAI/bge-m3`, ~2.3GB). On this development machine
(8GB RAM), loading bge-m3 caused severe swap thrashing (confirmed via
`vm_stat`/`sysctl vm.swapusage` — 6.9GB of 8GB swap already in use) and
made both `mps` and `cpu` device loading impractically slow — not a bug
in this module, but a real resource constraint that's exactly why the
project default was changed to this smaller model. See
embeddings.py's module docstring for the full investigation.

Tests that don't need a loaded model at all (the prefix logic, device
resolution) are pure unit tests with no model I/O.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.retriever.embeddings import (
    EmbeddingModel,
    _QueryDocumentPrefixer,
    _resolve_device,
)

SMALL_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# ---------------------------------------------------------------------------
# _QueryDocumentPrefixer — pure logic, no model loading
# ---------------------------------------------------------------------------


def test_e5_prefixer_adds_query_and_passage_prefixes():
    prefixer = _QueryDocumentPrefixer("intfloat/multilingual-e5-large")
    assert prefixer.for_query("Fuqarolik huquqi nima?") == "query: Fuqarolik huquqi nima?"
    assert prefixer.for_document("1-modda matni") == "passage: 1-modda matni"


def test_bge_m3_prefixer_adds_no_prefix():
    prefixer = _QueryDocumentPrefixer("BAAI/bge-m3")
    assert prefixer.for_query("test") == "test"
    assert prefixer.for_document("test") == "test"


def test_bge_large_prefixer_adds_query_instruction_only():
    prefixer = _QueryDocumentPrefixer("BAAI/bge-large-en-v1.5")
    query = prefixer.for_query("test")
    assert query.startswith("Represent this sentence for searching relevant passages: ")
    assert query.endswith("test")
    # No prefix on documents for the BGE family.
    assert prefixer.for_document("test") == "test"


def test_unknown_model_prefixer_adds_no_prefix():
    prefixer = _QueryDocumentPrefixer("some-org/some-random-model")
    assert prefixer.for_query("test") == "test"
    assert prefixer.for_document("test") == "test"


def test_prefixer_is_case_insensitive():
    prefixer = _QueryDocumentPrefixer("INTFLOAT/MULTILINGUAL-E5-LARGE")
    assert prefixer.for_query("x") == "query: x"


# ---------------------------------------------------------------------------
# _resolve_device — pure logic
# ---------------------------------------------------------------------------


def test_resolve_device_passes_through_explicit_choice():
    assert _resolve_device("cpu") == "cpu"
    assert _resolve_device("cuda") == "cuda"
    assert _resolve_device("mps") == "mps"


def test_resolve_device_auto_returns_a_valid_device():
    resolved = _resolve_device("auto")
    assert resolved in ("cuda", "mps", "cpu")


# ---------------------------------------------------------------------------
# EmbeddingModel — loads the small model once, shared across tests in this
# module via a module-scoped fixture, to avoid repeated multi-second loads.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def small_model() -> EmbeddingModel:
    return EmbeddingModel(model_name=SMALL_MODEL, device="cpu")


def test_dimension_matches_known_model_output(small_model: EmbeddingModel):
    assert small_model.dimension == 384  # known output size for this model


def test_embed_documents_shape_and_dtype(small_model: EmbeddingModel):
    texts = ["1-modda. Qonun matni.", "2-modda. Boshqa qonun matni."]
    vecs = small_model.embed_documents(texts)
    assert vecs.shape == (2, small_model.dimension)
    assert vecs.dtype == np.float32


def test_embed_documents_empty_list_returns_empty_array(small_model: EmbeddingModel):
    vecs = small_model.embed_documents([])
    assert vecs.shape == (0, small_model.dimension)


def test_embeddings_are_l2_normalized(small_model: EmbeddingModel):
    vecs = small_model.embed_documents(["Fuqarolik qonunchiligi.", "Mehnat kodeksi."])
    norms = np.linalg.norm(vecs, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)


def test_embed_query_shape(small_model: EmbeddingModel):
    vec = small_model.embed_query("Fuqarolik huquqi nima?")
    assert vec.shape == (small_model.dimension,)
    assert abs(np.linalg.norm(vec) - 1.0) < 1e-5


def test_relevant_document_ranks_higher_by_cosine_similarity(small_model: EmbeddingModel):
    """A basic sanity check that the embedding space is semantically
    meaningful: a document about civil law should score higher against a
    civil-law query than an unrelated labor-law document."""
    docs = [
        "Fuqarolik shartnomasi ikki taraf o'rtasida tuziladigan bitim hisoblanadi.",
        "Ish beruvchi xodimga har oy ish haqi to'lashi shart.",
    ]
    doc_vecs = small_model.embed_documents(docs)
    query_vec = small_model.embed_query("Fuqarolik shartnomasi qanday tuziladi?")

    similarities = doc_vecs @ query_vec
    assert similarities[0] > similarities[1]


def test_same_model_and_device_reuses_cached_instance():
    """The module-level lru_cache means two EmbeddingModel instances with
    identical (model_name, device) share the same underlying
    SentenceTransformer object — verified by identity, not just equality."""
    a = EmbeddingModel(model_name=SMALL_MODEL, device="cpu")
    b = EmbeddingModel(model_name=SMALL_MODEL, device="cpu")
    assert a._model is b._model
