"""
Local speech-to-text via faster-whisper (CTranslate2's Whisper reimplementation).

WHY faster-whisper OVER openai-whisper OR A HOSTED API
--------------------------------------------------------------
This mirrors the project's existing "local-first, cloud optional" stance
(`LLM_PROVIDER=ollama` as the default over `gemini`): the mic button should
work fully offline, with no API key and no per-request cost. faster-whisper
runs the same Whisper model weights through CTranslate2 instead of PyTorch,
which is several times faster on CPU — the realistic deployment target for
this project (see `EMBEDDING_DEVICE`'s "8GB-RAM dev machine" note in
`app/config/settings.py`) — while producing equivalent transcriptions.

WHY A PROCESS-WIDE MODEL CACHE (mirrors `embeddings.py`'s `_load_sentence_transformer`)
------------------------------------------------------------------------------------------
Loading Whisper weights from disk is expensive (seconds, plus the download
on first run). `api/dependencies.get_transcriber_cached()` builds ONE
`WhisperTranscriber` per process and reuses it across every `/api/transcribe`
request, exactly like `get_pipeline()`/`get_llm_cached()` do for the RAG
pipeline and analysis LLM.
"""

from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.transcription.exceptions import EmptyAudioError, TranscriptionModelLoadError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _resolve_whisper_device(configured: str) -> str:
    """Resolve "auto" to cuda/cpu — CTranslate2 (faster-whisper's backend) has no
    MPS support, unlike the embedding/reranker models' `resolve_device()`, so
    "auto" on Apple Silicon correctly falls back to "cpu" rather than "mps".
    """
    if configured != "auto":
        return configured

    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


class WhisperTranscriber:
    """Thin wrapper around `faster_whisper.WhisperModel` — transcribe(audio_path) -> str."""

    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        language: str | None = ...,  # sentinel: None is a valid value (auto-detect)
    ) -> None:
        self.model_size = model_size or settings.whisper_model_size
        self.device = _resolve_whisper_device(device or settings.whisper_device)
        self.compute_type = compute_type or settings.whisper_compute_type
        self.language = settings.whisper_language if language is ... else language

        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise TranscriptionModelLoadError(
                "faster-whisper is not installed. Run `pip install -r requirements.txt`."
            ) from e

        logger.info(
            "Loading Whisper model '%s' on device='%s' compute_type='%s' ...",
            self.model_size,
            self.device,
            self.compute_type,
        )
        try:
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        except Exception as e:  # faster-whisper raises plain RuntimeError/ValueError on bad config
            raise TranscriptionModelLoadError(f"Failed to load Whisper model '{self.model_size}': {e}") from e
        logger.info("Whisper model loaded.")

    def transcribe(self, audio_path: Path) -> str:
        """Transcribe an audio file to text. Raises `EmptyAudioError` if no speech is detected."""
        segments, _info = self._model.transcribe(str(audio_path), language=self.language, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            raise EmptyAudioError("Audio ichida nutq aniqlanmadi.")
        return text
