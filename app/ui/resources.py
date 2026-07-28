"""
Cached, shared resources for the Streamlit UI.

WHY THIS MODULE EXISTS
-----------------------
Streamlit reruns a page's ENTIRE script top-to-bottom on every user
interaction (clicking a button, submitting a form, even just resizing a
widget) — a `MetadataRepository()` or `RAGPipeline()` constructed as a
plain module-level call would be rebuilt on every single rerun. For a
cheap object (`MetadataRepository`, which just opens a SQLite path) that
merely wastes a little time; for the expensive resources later milestones
will add here (an `EmbeddingModel`, a `RerankerModel`, an `OllamaLLM` —
each taking real seconds to load, per Milestones 5, 9, and 13's own
measurements), rebuilding on every rerun would make the UI painfully slow
and would repeatedly reload multi-hundred-MB model weights for no reason.

`st.cache_resource` is Streamlit's mechanism for exactly this: it caches
the return value of a decorated function across reruns (and across
sessions, within one running Streamlit process), so `get_repo()` — and
every heavier resource getter later milestones add here — only actually
constructs its object once per running app process, not once per click.

WHY OLLAMA CONNECTIVITY IS DELIBERATELY NOT CACHED
-------------------------------------------------------
Unlike a loaded model's weights (which don't change once loaded),
whether Ollama is currently reachable is exactly the kind of fact that
CAN change mid-session (a user stops `ollama serve` in another terminal,
or starts it after the Streamlit app was already running). Caching that
check would show a stale "connected" status after Ollama actually went
down, which is worse than useless for a status indicator — it would
actively mislead. `check_ollama_status()` is intentionally a plain,
uncached function: it's a fast local API call (tens of milliseconds), so
paying that cost on every page load that shows it (Home, Settings) is
cheap insurance against showing wrong information.
"""

from __future__ import annotations

import streamlit as st

from app.database import MetadataRepository


@st.cache_resource
def get_repo() -> MetadataRepository:
    """The shared metadata repository, constructed once per app process."""
    return MetadataRepository()


@st.cache_resource(show_spinner="Yordamchi tayyorlanmoqda (birinchi marta biroz vaqt olishi mumkin)...")
def get_pipeline():
    """The shared RAGPipeline, constructed once per app process.

    `RAGPipeline()` (Milestone 14) eagerly loads the embedding model and
    reranker (real, multi-second costs — see Milestones 5 and 9) and
    checks Ollama connectivity at construction. Caching this the same way
    as `get_repo()` is *why* the Chat page (Milestone 16) can respond
    quickly after the first load — without it, every single chat message
    would re-pay all of that startup cost.

    Deliberately NOT wrapped in try/except here: if construction fails
    (Ollama unreachable, configured model not pulled — `OllamaLLM` raises
    `LLMConnectionError`/`LLMModelNotFoundError`, Milestone 13), Streamlit
    does not cache a raised exception — the NEXT call to `get_pipeline()`
    will retry construction from scratch. That is exactly the right
    behavior for "Ollama was down, the user just started it": the retry
    happens automatically on the next rerun rather than requiring a
    stale failure to somehow be invalidated. The caller (`chat.py`)
    is responsible for catching the exception and showing a clear
    message — this function's only job is caching the success case.
    """
    from app.rag import RAGPipeline

    return RAGPipeline()


def check_ollama_status() -> tuple[bool, list[str], str]:
    """Check Ollama connectivity right now (never cached — see module docstring).

    Returns (is_connected, available_models, error_message).
    """
    from app.llm import list_available_models

    try:
        models = list_available_models()
        return True, models, ""
    except Exception as e:  # noqa: BLE001 - surfaced to the UI as a status message
        return False, [], str(e)
