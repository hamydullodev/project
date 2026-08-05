"""
POST /api/analyze-document — upload one document, stream back an AI analysis.

WHY THIS IS A SEPARATE ENDPOINT FROM /api/ask, NOT A VARIANT OF IT
------------------------------------------------------------------------
`/api/ask` answers questions FROM the indexed law corpus via
`RAGPipeline` (retrieval -> rerank -> compress -> generate). This
endpoint has no retrieval step at all — the only input is the text of
ONE uploaded file. Bolting a "file" parameter onto `/api/ask` would
conflate two genuinely different operations (search the corpus vs.
analyze a standalone document) behind one endpoint; keeping them
separate keeps each one's request shape and error cases honest.

WHY SSE, MIRRORING ask.py's EXACT EVENT PROTOCOL
------------------------------------------------------
Same reasoning as `ask.py`: the frontend wants to render analysis text
as it's generated, not wait for the full response. Reusing the same
`event: info` (analogous to `ask.py`'s `event: sources` — sent once,
immediately) / `event: token` / `event: done` / `event: error` shape
means the frontend's SSE parser (`lib/api.ts`) is copy-pasted with
different field names, not reinvented.

WHY THE UPLOAD IS WRITTEN TO A TEMP FILE INSTEAD OF PARSED IN MEMORY
--------------------------------------------------------------------------
`app.ingestion.loaders.load_for_analysis` (and everything it calls —
PyMuPDF, python-docx, pytesseract) expects a filesystem `Path`, not raw
bytes — matching every existing loader in this project, all of which are
built around `IndexingPipeline` reading real files from disk. Writing the
upload to a `NamedTemporaryFile` with the ORIGINAL extension preserved
(so format sniffing by extension still works) reuses that exact code
path instead of forking a parallel in-memory variant of every loader.
The temp file is always removed in a `finally` block, whether loading
succeeds or fails.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from api.dependencies import get_llm_cached
from app.config import settings
from app.ingestion import ANALYSIS_SUPPORTED_EXTENSIONS, load_for_analysis
from app.ingestion.exceptions import CorruptedDocumentError, EmptyDocumentError, UnsupportedFileTypeError
from app.llm import GeminiLLM, LLMConnectionError, LLMError, LLMModelNotFoundError, OllamaLLM
from app.prompts import build_analysis_messages
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _llm_dependency() -> OllamaLLM | GeminiLLM:
    try:
        return get_llm_cached()
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_analysis(
    llm: OllamaLLM | GeminiLLM, document_text: str, file_name: str, char_count: int, warnings: list[str]
) -> Iterator[str]:
    """Plain (non-async) generator, same as `ask.py`'s `_stream_answer` — Starlette
    runs a sync generator passed to `StreamingResponse` in a worker thread,
    so the blocking `llm.stream()` network call doesn't stall the event loop.
    """
    yield _sse("info", {"file_name": file_name, "char_count": char_count, "warnings": warnings})

    try:
        messages = build_analysis_messages(document_text, file_name)
        for chunk in llm.stream(messages):
            yield _sse("token", {"text": chunk})
    except LLMError as e:
        yield _sse("error", {"message": str(e)})
        return

    yield _sse("done", {})


@router.post("/analyze-document")
async def analyze_document(
    file: UploadFile, llm: OllamaLLM | GeminiLLM = Depends(_llm_dependency)
) -> StreamingResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ANALYSIS_SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Qo'llab-quvvatlanmaydigan fayl turi '{suffix}'. "
            f"Ruxsat etilgan: {sorted(ANALYSIS_SUPPORTED_EXTENSIONS)}",
        )

    contents = await file.read()
    if len(contents) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Fayl juda katta ({len(contents)} bayt). "
            f"Ruxsat etilgan maksimal hajm: {settings.max_upload_size_bytes} bayt.",
        )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(contents)
            tmp_path = Path(tmp_file.name)

        loaded = load_for_analysis(tmp_path)
    except (UnsupportedFileTypeError, EmptyDocumentError, CorruptedDocumentError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    file_name = file.filename or "hujjat"
    logger.info(
        "Analyzing uploaded document: name=%s chars=%d warnings=%d",
        file_name,
        loaded.char_count,
        len(loaded.warnings),
    )

    return StreamingResponse(
        _stream_analysis(llm, loaded.full_text, file_name, loaded.char_count, loaded.warnings),
        media_type="text/event-stream",
    )
