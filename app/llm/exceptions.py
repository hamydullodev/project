"""
Exception hierarchy for local LLM (Ollama) failures.

WHY THIS MODULE EXISTS
-----------------------
Mirrors the same reasoning as `app.ingestion.exceptions` and
`app.retriever.vector_store.VectorStoreError`: a caller (the RAG
pipeline, Milestone 14; the Streamlit UI, later milestones) needs to
catch ONE well-defined exception type per failure category and show the
user something actionable, rather than a raw `ConnectionError` or
`ollama.ResponseError` traceback. A local-LLM app has two failure modes a
user will realistically hit — Ollama isn't running, or the configured
model hasn't been pulled — and each deserves a distinct, specific error
message telling the user exactly what command fixes it.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base class for all local LLM failures."""


class LLMConnectionError(LLMError):
    """Raised when the Ollama daemon isn't reachable at the configured URL."""


class LLMModelNotFoundError(LLMError):
    """Raised when the configured model isn't pulled locally."""
