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

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.database import CollectionSummary
    from app.reranker import RerankedResult


class AskRequest(BaseModel):
    """The request body for `POST /api/ask`."""

    query: str = Field(..., min_length=1, description="The user's question, in Uzbek.")
    collection_ids: list[str] | None = Field(
        default=None,
        description="Optional scope: only search within these collection ids "
        "(see GET /api/collections). Omit/null to search the entire corpus.",
    )


class SourceOut(BaseModel):
    """One cited source chunk, as sent to the frontend's sources panel."""

    chunk_id: str
    law_name: str | None = None
    collection_id: str | None = None
    collection_category: str | None = None
    collection_title: str | None = None
    article_number: str | None = None
    section: str | None = None
    page_number: int | None = None
    text: str
    dense_score: float | None = None
    sparse_score: float | None = None
    # `dense_score`/`sparse_score` above are the RAW scores (BM25's
    # sparse_score in particular is an unbounded relevance score, not a
    # [0, 1] value — a frontend that renders it as a percentage produces
    # nonsense like "3802%"). These two are the min-max NORMALIZED
    # variants `HybridRetriever` already computes for score fusion (see
    # `app/retriever/hybrid_retriever.py`) — genuinely [0, 1], safe to
    # render as a percentage bar.
    dense_score_normalized: float | None = None
    sparse_score_normalized: float | None = None
    combined_score: float
    reranker_score: float

    @classmethod
    def from_reranked(cls, r: RerankedResult) -> SourceOut:
        return cls(
            chunk_id=r.chunk_id,
            law_name=r.law_name,
            collection_id=r.collection_id,
            collection_category=r.collection_category,
            collection_title=r.collection_title,
            article_number=r.article_number,
            section=r.section,
            page_number=r.page_number,
            text=r.text,
            dense_score=r.dense_score,
            sparse_score=r.sparse_score,
            dense_score_normalized=r.dense_score_normalized,
            sparse_score_normalized=r.sparse_score_normalized,
            combined_score=r.combined_score,
            reranker_score=r.reranker_score,
        )


class HealthResponse(BaseModel):
    """The response body for `GET /api/health`."""

    llm_provider: str
    ollama_connected: bool
    ollama_models: list[str]
    llm_model: str
    embedding_model: str
    total_documents: int
    total_chunks: int


class CollectionOut(BaseModel):
    """One entry of `GET /api/collections` — a scopeable law/collection."""

    collection_id: str
    category: str | None = None
    title: str | None = None
    num_documents: int
    num_chunks: int
    source_url: str | None = None

    @classmethod
    def from_summary(cls, s: CollectionSummary) -> CollectionOut:
        return cls(
            collection_id=s.collection_id,
            category=s.category,
            title=s.title,
            num_documents=s.num_documents,
            num_chunks=s.num_chunks,
            source_url=s.source_url,
        )
