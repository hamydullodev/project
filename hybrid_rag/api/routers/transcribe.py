"""
POST /api/transcribe — upload a short audio recording, get back its transcript.

WHY A PLAIN JSON RESPONSE, NOT SSE (unlike ask.py/analyze.py)
---------------------------------------------------------------------
Those endpoints stream because an LLM answer arrives token-by-token over
seconds and the frontend renders it live. A mic-button transcription is the
opposite: faster-whisper only produces a result once the WHOLE recording has
been decoded, so there is nothing to stream — a single `{"text": "..."}\`
response (`{"text": "..."}`) is both simpler and exactly as fast as SSE would be here.

WHY THE UPLOAD IS WRITTEN TO A TEMP FILE (mirrors analyze.py's reasoning)
--------------------------------------------------------------------------
`faster_whisper.WhisperModel.transcribe()` (via `WhisperTranscriber.transcribe`)
takes a filesystem path, not raw bytes. Writing the browser's recording
(webm/opus from `MediaRecorder`, typically) to a `NamedTemporaryFile` and
handing that path to `WhisperTranscriber` reuses the same
decode-whatever-container-ffmpeg-supports path faster-whisper already has,
instead of adding an in-memory audio-decoding dependency. Always removed in
a `finally` block, success or failure.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from api.dependencies import get_transcriber_cached
from app.config import settings
from app.transcription import EmptyAudioError, TranscriptionError, TranscriptionModelLoadError, WhisperTranscriber
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _transcriber_dependency() -> WhisperTranscriber:
    try:
        return get_transcriber_cached()
    except TranscriptionModelLoadError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile, transcriber: WhisperTranscriber = Depends(_transcriber_dependency)
) -> dict:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Bo'sh audio fayl yuborildi.")
    if len(contents) > settings.max_audio_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Audio fayl juda katta ({len(contents)} bayt). "
            f"Ruxsat etilgan maksimal hajm: {settings.max_audio_upload_size_bytes} bayt.",
        )

    suffix = Path(file.filename or "").suffix or ".webm"
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(contents)
            tmp_path = Path(tmp_file.name)

        text = transcriber.transcribe(tmp_path)
    except EmptyAudioError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except TranscriptionError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    logger.info("Transcribed audio: name=%s chars=%d", file.filename, len(text))
    return {"text": text}
