"""
POST /api/ask — ask a question, streaming the answer as Server-Sent Events.

WHY SSE (`text/event-stream`), NOT A PLAIN JSON RESPONSE
------------------------------------------------------------
The frontend's whole point (a large search box that renders an answer
inline, with a typing effect, per the design brief) needs tokens as
they're generated, not one JSON blob after the full answer is ready —
the same reason `RAGPipeline.ask_stream()`/`OllamaLLM.stream()` exist at
all (see their own docstrings). SSE is the standard, simple choice for
one-directional server-to-browser streaming over plain HTTP: the browser's
native `EventSource` (or a `fetch()` + `ReadableStream` reader, which the
Next.js frontend uses instead, to also send a `POST` body — `EventSource`
is GET-only) parses `event:`/`data:` lines with zero extra client
dependency, and it needs no new server dependency beyond FastAPI's own
`StreamingResponse` (a raw SSE formatter is ~3 lines — not worth adding
a library like `sse-starlette` for).

THE EVENT PROTOCOL (what the frontend parses)
-----------------------------------------------------
  - `event: sources` — sent once, immediately, before any answer text.
    `data`: `{"query": str, "sources": SourceOut[]}` — lets the frontend
    render the sources panel right away, exactly mirroring why
    `RAGPipeline.ask_stream()` returns `context` before the answer starts
    streaming (see that method's docstring).
  - `event: token` — sent repeatedly as the LLM generates. `data`:
    `{"text": str}` — one incremental text chunk to append to the answer.
  - `event: done` — sent once, at the end. `data`:
    `{"answer_found": bool}` — mirrors `RAGAnswer.answer_found`
    (`app/rag/pipeline.py`), so the frontend can style a "not found"
    answer differently without re-implementing the fallback-phrase check.
  - `event: error` — sent if generation fails mid-stream (e.g. Ollama
    goes down partway through). `data`: `{"message": str}`.

WHY VALIDATION HAPPENS BEFORE THE `StreamingResponse` IS CREATED, NOT INSIDE IT
------------------------------------------------------------------------------------------
Once a `StreamingResponse` starts sending, the HTTP status code (200) is
already committed to the client — there is no way to "downgrade" to a
400 or 503 partway through a stream. So `ask()` resolves the pipeline
(via `Depends(_pipeline_dependency)`) and calls `pipeline.retrieve()`
ITSELF, synchronously, catching their specific exceptions and raising a
real `HTTPException` with the correct status code for each — only once
both succeed does it hand off to `_stream_answer()` for the part that's
actually meant to stream (the LLM call, via
`RAGPipeline.stream_from_context()` — see that method's own docstring
for why it exists as a separate method from `ask_stream()` specifically
to make this split possible).

WHY `Depends(_pipeline_dependency)` RATHER THAN CALLING `get_pipeline()` INLINE
------------------------------------------------------------------------------------------
Routing the pipeline through FastAPI's dependency-injection system (not
just calling `api.dependencies.get_pipeline()` directly inside the route
body) makes it swappable in tests via `app.dependency_overrides
[_pipeline_dependency] = lambda: fake_pipeline` — `tests/test_api.py`
uses exactly this to test the streaming response's SSE framing with a
stub pipeline, without needing a real Ollama server or loaded embedding
model for that specific test.
"""

from __future__ import annotations

import json
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.llm import LLMConnectionError, LLMModelNotFoundError
from app.prompts import NOT_FOUND_MESSAGE_UZ
from app.rag import EmptyQueryError, RAGPipeline, RetrievalContext
from api.dependencies import get_pipeline
from api.schemas import AskRequest, SourceOut

router = APIRouter()


def _pipeline_dependency() -> RAGPipeline:
    try:
        return get_pipeline()
    except (LLMConnectionError, LLMModelNotFoundError) as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_answer(pipeline: RAGPipeline, context: RetrievalContext) -> Iterator[str]:
    sources = [SourceOut.from_reranked(r).model_dump() for r in context.compression.kept]
    yield _sse("sources", {"query": context.query, "sources": sources})

    full_text_parts: list[str] = []
    try:
        for chunk in pipeline.stream_from_context(context):
            full_text_parts.append(chunk)
            yield _sse("token", {"text": chunk})
    except (LLMConnectionError, LLMModelNotFoundError) as e:
        yield _sse("error", {"message": str(e)})
        return

    answer_text = "".join(full_text_parts)
    yield _sse("done", {"answer_found": NOT_FOUND_MESSAGE_UZ not in answer_text})


@router.post("/ask")
def ask(request: AskRequest, pipeline: RAGPipeline = Depends(_pipeline_dependency)) -> StreamingResponse:
    try:
        context = pipeline.retrieve(request.query)
    except EmptyQueryError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return StreamingResponse(_stream_answer(pipeline, context), media_type="text/event-stream")
