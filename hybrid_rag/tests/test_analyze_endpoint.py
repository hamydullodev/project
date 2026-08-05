"""
Unit tests for POST /api/analyze-document (api/routers/analyze.py).

Same stub-over-dependency-injection approach as tests/test_api.py's
`/api/ask` tests (see that file's docstring for the full rationale) —
`_llm_dependency` is swapped via `app.dependency_overrides` so most tests
here run in milliseconds with no real Gemini/Ollama call. One real,
unmocked end-to-end test at the bottom mirrors
`test_ask_end_to_end_with_real_pipeline`.
"""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.analyze import _llm_dependency

client = TestClient(app)


class _StubLLM:
    """Duck-types the one method `analyze.py` actually calls."""

    def __init__(self, tokens: list[str]):
        self._tokens = tokens

    def stream(self, messages):
        return iter(self._tokens)


class _RaisingLLM:
    def stream(self, messages):
        raise AssertionError("LLM.stream() should not be called when the upload is rejected first")


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = block.splitlines()
        event = next(line.split(": ", 1)[1] for line in lines if line.startswith("event: "))
        data = next(line.split(": ", 1)[1] for line in lines if line.startswith("data: "))
        events.append((event, json.loads(data)))
    return events


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_analyze_rejects_unsupported_extension():
    app.dependency_overrides[_llm_dependency] = lambda: _RaisingLLM()
    response = client.post(
        "/api/analyze-document",
        files={"file": ("virus.exe", io.BytesIO(b"not a document"), "application/octet-stream")},
    )
    assert response.status_code == 400


def test_analyze_rejects_oversized_upload(monkeypatch):
    app.dependency_overrides[_llm_dependency] = lambda: _RaisingLLM()
    monkeypatch.setattr("api.routers.analyze.settings.max_upload_size_bytes", 10)
    response = client.post(
        "/api/analyze-document",
        files={"file": ("test.txt", io.BytesIO(b"this is way more than 10 bytes"), "text/plain")},
    )
    assert response.status_code == 413


def test_analyze_rejects_empty_document():
    app.dependency_overrides[_llm_dependency] = lambda: _RaisingLLM()
    response = client.post(
        "/api/analyze-document",
        files={"file": ("empty.txt", io.BytesIO(b"   \n\n  "), "text/plain")},
    )
    assert response.status_code == 422


def test_analyze_streams_info_then_tokens_then_done():
    stub = _StubLLM(tokens=["## Xulosa", "\nBu sinov hujjati."])
    app.dependency_overrides[_llm_dependency] = lambda: stub

    response = client.post(
        "/api/analyze-document",
        files={"file": ("shartnoma.txt", io.BytesIO("1-modda. Sinov shartnomasi matni.".encode()), "text/plain")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    assert events[0][0] == "info"
    assert events[0][1]["file_name"] == "shartnoma.txt"
    assert events[0][1]["char_count"] > 0
    assert events[-1][0] == "done"
    token_text = "".join(data["text"] for name, data in events if name == "token")
    assert token_text == "## Xulosa\nBu sinov hujjati."


def _llm_reachable() -> bool:
    from app.llm import get_llm

    try:
        get_llm()
        return True
    except Exception:  # noqa: BLE001 - any failure means "treat as unreachable" for this skip check
        return False


@pytest.mark.skipif(not _llm_reachable(), reason="No configured LLM (Ollama/Gemini) is reachable")
def test_analyze_document_end_to_end_with_real_llm():
    """One real, unmocked request through the actual configured LLM
    (Gemini or Ollama, per `.env`) — proves the stub's assumed
    `.stream(messages)` interface actually matches the real client, same
    purpose as `test_api.py`'s `test_ask_end_to_end_with_real_pipeline`.
    """
    from api.dependencies import reset_llm_cache

    reset_llm_cache()
    response = client.post(
        "/api/analyze-document",
        files={
            "file": (
                "kichik_hujjat.txt",
                io.BytesIO(
                    "1-modda. Ushbu hujjat ijara shartnomasi namunasidir. "
                    "Ijarachi har oyning 5-sanasigacha ijara haqini toʻlashi shart.".encode()
                ),
                "text/plain",
            )
        },
    )
    assert response.status_code == 200
    events = _parse_sse(response.text)
    assert events[0][0] == "info"
    assert events[-1][0] in ("done", "error")
    token_text = "".join(data["text"] for name, data in events if name == "token")
    assert token_text.strip()
