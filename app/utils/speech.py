"""Local speech-to-text (Whisper via faster-whisper).

Runs entirely on-device, same as the LLM — no cloud STT API/key involved.
The model weights download once (from Hugging Face) the first time this is
called and are cached locally afterwards.
"""

from __future__ import annotations

from typing import BinaryIO

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        settings = get_settings()
        logger.info("Loading Whisper model '{}'...", settings.whisper_model_size)
        _model = WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")
    return _model


def transcribe_audio(audio_file: BinaryIO) -> str:
    """Transcribe a WAV audio file-like object to text.

    The language is pinned via ``WHISPER_LANGUAGE`` (default "uz") rather
    than left to auto-detection — Whisper's language detector frequently
    misclassifies short Uzbek clips as a related language (Turkish,
    Russian, ...), transcribing gibberish in the wrong alphabet/language.
    """
    model = _get_model()
    settings = get_settings()
    segments, _info = model.transcribe(audio_file, language=settings.whisper_language, vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()
