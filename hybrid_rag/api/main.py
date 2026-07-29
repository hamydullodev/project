"""
FastAPI application entry point — `python run_api.py` (project root) runs
this via uvicorn, the same "one documented command" pattern `run.py`
established for the Streamlit UI.

WHY CORS IS CONFIGURED HERE AT ALL
---------------------------------------
The Next.js frontend (Milestone 2 onward) runs as its OWN process on its
own port (`localhost:3000` in development) — a fundamentally different
origin from this API's `localhost:8000`, even though both run on the same
machine. Browsers block cross-origin `fetch()` calls by default; without
explicit CORS headers here, every request the frontend makes to `/api/*`
would fail silently before this code even runs. `APISettings.cors_origins`
(default: `localhost:3000`/`127.0.0.1:3000`) is the allow-list — see
`api/config.py` for how to override it via `.env` for a different port or
a production deployment.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_api_settings
from api.routers import ask, health

api_settings = get_api_settings()

app = FastAPI(
    title="Hybrid RAG API — Oʻzbekiston Qonunchiligi",
    description="Thin HTTP layer over app.rag.RAGPipeline, for the Next.js frontend.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=api_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(ask.router, prefix="/api", tags=["ask"])


@app.get("/")
def root() -> dict:
    """A trivial liveness check at the bare root — `/api/health` has the real status."""
    return {"service": "hybrid-rag-api", "status": "ok"}
