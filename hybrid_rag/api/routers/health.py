"""
GET /api/health — corpus size and Ollama connectivity, for the frontend's status indicator.

WHY THIS DOESN'T GO THROUGH `get_pipeline()`
------------------------------------------------
`RAGPipeline()` construction itself FAILS if Ollama is unreachable (see
`api/dependencies.py`) — using it here would make a health CHECK unable
to report "Ollama is down" as a normal, successful response, which is
exactly the information this endpoint exists to surface. Instead this
queries `MetadataRepository` (cheap, always available — SQLite is a local
file) and `list_available_models()` (a fast, independent Ollama call)
directly, mirroring `app/ui/resources.py`'s `check_ollama_status()`,
which makes the identical choice for the Streamlit UI's status badge.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.database import MetadataRepository
from app.llm import list_available_models
from api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    repo = MetadataRepository()
    stats = repo.get_statistics()

    try:
        models = list_available_models()
        connected = True
    except Exception:  # noqa: BLE001 - any failure here means "not connected", surfaced as data
        models = []
        connected = False

    return HealthResponse(
        ollama_connected=connected,
        ollama_models=models,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        total_documents=stats["total_documents"],
        total_chunks=stats["total_chunks"],
    )
