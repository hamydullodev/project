"""
Exception hierarchy for speech-to-text failures — mirrors `app.llm.exceptions`'
reasoning: one well-defined type per failure category so `api/routers/transcribe.py`
can map each to a specific HTTP status instead of a raw 500.
"""

from __future__ import annotations


class TranscriptionError(Exception):
    """Base class for all speech-to-text failures."""


class TranscriptionModelLoadError(TranscriptionError):
    """Raised when the faster-whisper model fails to load (missing weights, bad device/compute_type)."""


class EmptyAudioError(TranscriptionError):
    """Raised when the uploaded audio contains no detectable speech."""
