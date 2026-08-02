"""LLM access, local (Ollama) or hosted (Gemini) — see `get_llm()`."""

from app.config import settings
from app.llm.exceptions import LLMConnectionError, LLMError, LLMModelNotFoundError
from app.llm.gemini_client import GeminiLLM
from app.llm.ollama_client import OllamaLLM, list_available_models


def get_llm(max_tokens: int | None = None) -> OllamaLLM | GeminiLLM:
    """Construct the LLM backend configured via `settings.llm_provider`.

    The one place that decides which provider is active — every caller
    (chiefly `RAGPipeline.__init__`) just calls `get_llm()` instead of
    importing a specific provider class, so `LLM_PROVIDER` in `.env` is a
    true drop-in switch.

    `max_tokens`, when given, overrides `settings.llm_max_tokens` for
    this instance — used by the document-analysis endpoint
    (`api/routers/analyze.py`), whose long, multi-section output needs a
    much larger budget than a typical `/api/ask` answer (see
    `settings.document_analysis_max_tokens`'s docstring for why).
    """
    if settings.llm_provider == "gemini":
        return GeminiLLM(max_tokens=max_tokens)
    return OllamaLLM(max_tokens=max_tokens)


__all__ = [
    "OllamaLLM",
    "GeminiLLM",
    "get_llm",
    "list_available_models",
    "LLMError",
    "LLMConnectionError",
    "LLMModelNotFoundError",
]
