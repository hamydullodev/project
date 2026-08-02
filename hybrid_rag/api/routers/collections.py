"""
GET /api/collections — list every indexed law/collection, for a "Browse Laws"
picker and for scoping `POST /api/ask` via `AskRequest.collection_ids`.

Reads straight from `MetadataRepository` (cheap, always available — same
reasoning as `health.py` not going through `get_pipeline()`), so this
endpoint works even before the RAG pipeline (embedding model, reranker,
LLM connectivity) has been constructed.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas import CollectionOut
from app.database import MetadataRepository

router = APIRouter()


@router.get("/collections", response_model=list[CollectionOut])
def list_collections() -> list[CollectionOut]:
    repo = MetadataRepository()
    return [CollectionOut.from_summary(s) for s in repo.get_collections()]
