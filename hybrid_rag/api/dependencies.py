"""
Shared FastAPI dependency: a process-wide `RAGPipeline` singleton.

WHY THIS MODULE EXISTS
-----------------------
Constructing `RAGPipeline()` is expensive — it loads the embedding model
and reranker into memory and checks Ollama connectivity (see
`app/rag/pipeline.py`). Exactly like `app/ui/resources.py`'s
`get_pipeline()` does for the Streamlit UI (via `st.cache_resource`),
this API builds it once per process and reuses it across requests rather
than once per request.

WHY A FAILED CONSTRUCTION IS NOT CACHED
-------------------------------------------
If Ollama isn't running yet when a request arrives, `RAGPipeline()`
raises `LLMConnectionError`/`LLMModelNotFoundError`. Caching that failure
would mean the API stays broken until the process restarts even after
Ollama comes up — so a failed construction is simply retried on the NEXT
request instead. Same reasoning `app/ui/resources.py.get_pipeline()`
documents for why it's deliberately not wrapped in try/except.

WHY A PLAIN MODULE-LEVEL GLOBAL, NOT `functools.lru_cache`
------------------------------------------------------------------
`lru_cache` caches a raised exception's absence, not its presence — a
call that raises simply never populates the cache, so a plain `if
_pipeline is None` guard around a module-level variable does exactly
what's needed here without any extra machinery. `reset_pipeline_cache()`
exists purely for tests that need a fresh instance (e.g. after
monkeypatching config), the same purpose `st.cache_resource.clear()`
serves for the Streamlit UI's tests.
"""

from __future__ import annotations

from app.config import settings
from app.llm import GeminiLLM, OllamaLLM, get_llm
from app.rag import RAGPipeline
from app.transcription import WhisperTranscriber

_pipeline: RAGPipeline | None = None
_llm: OllamaLLM | GeminiLLM | None = None
_transcriber: WhisperTranscriber | None = None


def get_pipeline() -> RAGPipeline:
    """Return the shared `RAGPipeline`, constructing it on first (successful) call."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


def reset_pipeline_cache() -> None:
    """Force the next `get_pipeline()` call to construct a fresh instance. Test-only."""
    global _pipeline
    _pipeline = None


def get_llm_cached() -> OllamaLLM | GeminiLLM:
    """Return the shared LLM client for the document-analysis endpoint.

    A separate cache from `get_pipeline()` — the analyze endpoint (no
    retrieval involved) shouldn't pay for loading the embedding model and
    reranker `RAGPipeline()` eagerly constructs, just to reach the LLM
    client. Same lazy-singleton, don't-cache-failure pattern as
    `get_pipeline()` above (see its docstring for why).

    Uses `settings.document_analysis_max_tokens` (larger than `/api/ask`'s
    `LLM_MAX_TOKENS`) since this client is ONLY ever used for document
    analysis, never for `/api/ask` (which gets its own LLM instance,
    default-sized, from inside `RAGPipeline.__init__`).
    """
    global _llm
    if _llm is None:
        _llm = get_llm(max_tokens=settings.document_analysis_max_tokens)
    return _llm


def reset_llm_cache() -> None:
    """Force the next `get_llm_cached()` call to construct a fresh instance. Test-only."""
    global _llm
    _llm = None


def get_transcriber_cached() -> WhisperTranscriber:
    """Return the shared `WhisperTranscriber` for `/api/transcribe`, constructing it on
    first (successful) call. Same lazy-singleton, don't-cache-failure pattern as
    `get_llm_cached()` above — loading Whisper weights is expensive, so this is built
    once per process rather than once per request.
    """
    global _transcriber
    if _transcriber is None:
        _transcriber = WhisperTranscriber()
    return _transcriber


def reset_transcriber_cache() -> None:
    """Force the next `get_transcriber_cached()` call to construct a fresh instance. Test-only."""
    global _transcriber
    _transcriber = None
