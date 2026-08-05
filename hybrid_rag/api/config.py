"""
API-layer configuration — deliberately separate from `app.config.Settings`.

WHY THIS IS ITS OWN `Settings` CLASS, NOT ADDED TO `app.config.Settings`
-------------------------------------------------------------------------------
`app.config.Settings` (the project's original config, Milestone 1)
configures the RAG PIPELINE itself — chunking, retrieval weights, which
LLM/embedding/reranker models to use. Every one of its fields is
meaningful regardless of which consumer drives the pipeline (the
Streamlit UI, this API, a test, an evaluation script). `HOST`/`PORT`/
`CORS_ORIGINS` are meaningful ONLY to this HTTP layer — they say nothing
about how documents get indexed or questions get answered. Keeping them
in their own class means `app.config.Settings` stays focused on the RAG
pipeline (as every other module in `app/` already assumes), and this
entire `api/` package could be deleted someday without touching that
class at all.

WHY `API_` PREFIXED ENV VARS, SHARING THE SAME `.env` FILE
------------------------------------------------------------------
Both `Settings` and `APISettings` read from the project's single `.env`
file (one place to configure the whole project, matching the "one
`.env`, one documented setup" pattern the original spec asked for), but
`APISettings` uses `env_prefix="API_"` so its keys (`API_HOST`,
`API_PORT`, `API_CORS_ORIGINS`) can never collide with `Settings`'
unprefixed keys (`LLM_MODEL`, `CHUNK_SIZE`, ...) even though pydantic-
settings loads both classes from the same file.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class APISettings(BaseSettings):
    """Configuration for the FastAPI process itself (not the RAG pipeline)."""

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_comma_separated(cls, v):
        """Allow `API_CORS_ORIGINS=http://a,http://b` as a plain env string.

        Pydantic-settings can parse a JSON list from an env var, but a
        comma-separated string is the friendlier, more common convention
        for a list-of-origins env var — this accepts either.
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache(maxsize=1)
def get_api_settings() -> APISettings:
    """Process-wide `APISettings` singleton — mirrors `app.config.get_settings()`."""
    return APISettings()
