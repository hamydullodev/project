"""
Pydantic request/response models for the API's HTTP surface.

WHY THESE ARE SEPARATE FROM `app`'s OWN MODELS (e.g. `RerankedResult`)
------------------------------------------------------------------------------
`app.reranker.RerankedResult` (and `ChunkRecord`, `RetrievalContext`, ...)
are internal pipeline data structures — their shape is whatever the RAG
pipeline's stages naturally produce, and can change as pipeline internals
evolve. The API's response shape is a PUBLIC CONTRACT the Next.js frontend
codes against; letting the frontend depend directly on an internal
pipeline model's exact fields would mean any internal refactor risks
silently breaking the frontend. `SourceOut.from_reranked()` is the one
place that translates between the two, so that contract is explicit and
in one spot.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.reranker import RerankedResult


class AskRequest(BaseModel):
    """The request body for `POST /api/ask`."""

    query: str = Field(..., min_length=1, description="The user's question, in Uzbek.")


class SourceOut(BaseModel):
    """One cited source chunk, as sent to the frontend's sources panel."""

    chunk_id: str
    law_name: Optional[str] = None
    article_number: Optional[str] = None
    section: Optional[str] = None
    page_number: Optional[int] = None
    text: str
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None
    combined_score: float
    reranker_score: float

    @classmethod
    def from_reranked(cls, r: "RerankedResult") -> "SourceOut":
        return cls(
            chunk_id=r.chunk_id,
            law_name=r.law_name,
            article_number=r.article_number,
            section=r.section,
            page_number=r.page_number,
            text=r.text,
            dense_score=r.dense_score,
            sparse_score=r.sparse_score,
            combined_score=r.combined_score,
            reranker_score=r.reranker_score,
        )


class HealthResponse(BaseModel):
    """The response body for `GET /api/health`."""

    ollama_connected: bool
    ollama_models: list[str]
    llm_model: str
    embedding_model: str
    total_documents: int
    total_chunks: int
