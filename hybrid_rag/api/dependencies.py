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

from typing import Optional

from app.rag import RAGPipeline

_pipeline: Optional[RAGPipeline] = None


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
