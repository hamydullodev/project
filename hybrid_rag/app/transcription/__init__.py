"""Local speech-to-text (faster-whisper) — see `WhisperTranscriber`."""

from app.transcription.exceptions import EmptyAudioError, TranscriptionError, TranscriptionModelLoadError
from app.transcription.whisper_client import WhisperTranscriber

__all__ = [
    "WhisperTranscriber",
    "TranscriptionError",
    "TranscriptionModelLoadError",
    "EmptyAudioError",
]
