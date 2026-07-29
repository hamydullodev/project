"""
Unit tests for the FastAPI backend (api/), added alongside the Next.js
frontend rebuild.

WHY MOST TESTS HERE USE A STUB PIPELINE, UNLIKE `test_chat_page.py`'S
REAL-PIPELINE APPROACH
------------------------------------------------------------------------------
`test_chat_page.py`/`test_retrieval_debug_page.py` run against the real
`RAGPipeline` deliberately (see their own docstrings) because the
Streamlit UI has no clean seam to inject a fake one without rebuilding
significant test machinery. This API is different: `ask()`'s pipeline
argument is resolved through FastAPI's own dependency-injection system
(`Depends(_pipeline_dependency)`), which exists SPECIFICALLY to make it
swappable — `app.dependency_overrides` is the standard, intended way to
substitute a test double, and doing so here means most of this file's
tests run in milliseconds, need no loaded embedding/reranker model, and
need no running Ollama server. `test_ask_end_to_end_with_real_pipeline`
is the one exception: it exercises the REAL pipeline once, the same way
`test_retrieval_evaluation.py` does, to prove the stub's assumptions
about the real interface still hold and that the real integration
actually works — skipped cleanly if the real corpus/Ollama aren't
available, same pattern as that file.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.ask import _pipeline_dependency
from app.llm import LLMConnectionError, list_available_models
from app.rag import CompressionResult, RetrievalContext
from app.reranker import RerankedResult

client = TestClient(app)


def _fake_context(query: str = "sinov soʻrovi") -> RetrievalContext:
    source = RerankedResult(
        chunk_id="doc-1::00001",
        dense_score=0.82,
        sparse_score=6.5,
        dense_score_normalized=0.9,
        sparse_score_normalized=0.9,
        combined_score=0.9,
        reranker_score=0.95,
        text="Bu sinov uchun yozilgan modda matni.",
        law_name="Test kodeksi",
        article_number="1",
        section=None,
        page_number=None,
    )
    return RetrievalContext(
        query=query,
        hybrid_results=[],
        reranked=[source],
        compression=CompressionResult(kept=[source]),
    )


class _StubPipeline:
    """Duck-types the two methods `api/routers/ask.py` actually calls."""

    def __init__(self, tokens: list[str]):
        self._tokens = tokens

    def retrieve(self, raw_query: str) -> RetrievalContext:
        from app.rag import preprocess_query

        cleaned = preprocess_query(raw_query)  # raises EmptyQueryError for blank input, like the real pipeline
        return _fake_context(query=cleaned)

    def stream_from_context(self, context: RetrievalContext):
        return iter(self._tokens)


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = block.splitlines()
        event = next(l.split(": ", 1)[1] for l in lines if l.startswith("event: "))
        data = next(l.split(": ", 1)[1] for l in lines if l.startswith("data: "))
        events.append((event, json.loads(data)))
    return events


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_root_is_ok():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_reports_real_corpus_and_ollama_status():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["ollama_connected"], bool)
    assert isinstance(body["total_documents"], int)
    assert isinstance(body["total_chunks"], int)
    assert body["llm_model"]
    assert body["embedding_model"]


def test_ask_rejects_truly_empty_query_with_422():
    # Pydantic's Field(min_length=1) rejects "" before the route body runs at all.
    response = client.post("/api/ask", json={"query": ""})
    assert response.status_code == 422


def test_ask_rejects_whitespace_only_query_with_400():
    app.dependency_overrides[_pipeline_dependency] = lambda: _StubPipeline(tokens=["ignored"])
    response = client.post("/api/ask", json={"query": "   "})
    assert response.status_code == 400


def test_ask_streams_sources_then_tokens_then_done():
    stub = _StubPipeline(tokens=["Salom", ", ", "dunyo!"])
    app.dependency_overrides[_pipeline_dependency] = lambda: stub

    response = client.post("/api/ask", json={"query": "Ish beruvchi kim?"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    event_names = [name for name, _ in events]
    assert event_names == ["sources", "token", "token", "token", "done"]

    sources_event = events[0][1]
    assert sources_event["query"] == "Ish beruvchi kim?"
    assert sources_event["sources"][0]["law_name"] == "Test kodeksi"
    assert sources_event["sources"][0]["article_number"] == "1"

    token_texts = [data["text"] for name, data in events if name == "token"]
    assert "".join(token_texts) == "Salom, dunyo!"

    assert events[-1][1]["answer_found"] is True


def test_ask_marks_answer_not_found_when_fallback_phrase_present():
    from app.prompts import NOT_FOUND_MESSAGE_UZ

    stub = _StubPipeline(tokens=[NOT_FOUND_MESSAGE_UZ])
    app.dependency_overrides[_pipeline_dependency] = lambda: stub

    response = client.post("/api/ask", json={"query": "Notanish savol"})
    events = _parse_sse(response.text)
    assert events[-1][1]["answer_found"] is False


def test_ask_returns_503_when_ollama_is_unreachable(monkeypatch: pytest.MonkeyPatch):
    # No dependency_overrides here - this exercises the REAL
    # `_pipeline_dependency`'s try/except, not a bypassed stub, by making
    # the underlying get_pipeline() call fail the way it would if Ollama
    # were actually down.
    import api.routers.ask as ask_module

    def _raise(*args, **kwargs):
        raise LLMConnectionError("Ollama is not reachable at http://localhost:11434")

    monkeypatch.setattr(ask_module, "get_pipeline", _raise)

    response = client.post("/api/ask", json={"query": "Har qanday savol"})
    assert response.status_code == 503
    assert "Ollama" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Real end-to-end integration (skipped if Ollama/the real corpus aren't available)
# ---------------------------------------------------------------------------


def _ollama_reachable() -> bool:
    try:
        list_available_models()
        return True
    except Exception:  # noqa: BLE001 - any failure means "treat as unreachable" for this skip check
        return False


@pytest.mark.skipif(not _ollama_reachable(), reason="Ollama is not running")
def test_ask_end_to_end_with_real_pipeline():
    """One real, unmocked request through the actual RAGPipeline.

    Proves the stub's assumed interface (`.retrieve()`/
    `.stream_from_context()`) actually matches the real `RAGPipeline`, and
    that the real embedding model + reranker + Ollama integration works
    end to end through the HTTP layer, not just in isolation.
    """
    from api.dependencies import reset_pipeline_cache

    reset_pipeline_cache()
    response = client.post(
        "/api/ask", json={"query": "Ish beruvchi mehnat shartnomasini qanday bekor qiladi?"}
    )
    assert response.status_code == 200
    events = _parse_sse(response.text)
    assert events[0][0] == "sources"
    assert events[-1][0] == "done"
    token_text = "".join(data["text"] for name, data in events if name == "token")
    assert token_text.strip()
