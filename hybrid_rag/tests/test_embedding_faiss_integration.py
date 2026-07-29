"""
Regression test guarding against the torch/faiss OpenMP conflict.

WHY THIS TEST EXISTS
----------------------
While building Milestone 6, using real `sentence-transformers` (torch)
embeddings together with FAISS in the same process — embed real chunk
text, add the vectors to a FAISS index, then search it — reliably
segfaulted (exit code 139) on this project's macOS development machine.
The root cause and fix are documented in `app/__init__.py`: both PyTorch
and FAISS's pip wheels bundle their own separate OpenMP runtime, and
letting both run multi-threaded in the same process corrupts memory.
`app/__init__.py` forces single-threaded operation via environment
variables to prevent this.

This test exists so that if that fix is ever accidentally removed, or a
future dependency upgrade reintroduces the conflict in some other form,
the test suite catches it as an outright crash (pytest reports a crashed
worker / segfault) rather than the bug only surfacing later when a user
actually tries to build a real index. Unlike the unit tests in
`test_vector_store.py` (synthetic vectors only) and `test_embeddings.py`
(model behavior only), this test deliberately exercises both libraries
together, at a scale (500 real embeddings) large enough to have reliably
reproduced the crash during investigation.
"""

from __future__ import annotations

from app.retriever.embeddings import EmbeddingModel
from app.retriever.vector_store import FAISSVectorStore

SMALL_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def test_real_embeddings_survive_faiss_add_and_search():
    """Embed real text with torch, store in FAISS, search — must not crash.

    If this test crashes the pytest process entirely (rather than failing
    normally), that IS the regression: see the module docstring.
    """
    em = EmbeddingModel(model_name=SMALL_MODEL, device="cpu")
    texts = [f"1-modda. Sinov matni raqami {i} qonunchilik toʻgʻrisida." for i in range(500)]
    vecs = em.embed_documents(texts, show_progress=False)

    store = FAISSVectorStore(dimension=em.dimension)
    chunk_ids = [f"doc::{i:05d}" for i in range(500)]
    store.add(chunk_ids, vecs)
    assert len(store) == 500

    query_vec = em.embed_query("Qonunchilik toʻgʻrisidagi sinov matni")
    results = store.search(query_vec, top_k=5)

    assert len(results) == 5
    # Real, meaningful assertion beyond "didn't crash": results are
    # sorted best-first and scores are valid cosine similarities.
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)
    assert all(-1.0 <= s <= 1.0 for s in scores)
