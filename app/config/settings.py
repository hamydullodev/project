"""
Centralized application configuration.

WHY THIS MODULE EXISTS
-----------------------
Every other module in this project (loaders, chunker, embeddings, retriever,
reranker, LLM, UI pages) needs *some* configuration value: a model name, a
file path, a chunk size. Without a single source of truth, that
configuration ends up scattered as magic numbers and `os.getenv()` calls
across dozens of files, each with its own (possibly inconsistent) default
and no validation.

This module solves that by:
  1. Reading every configurable value from ONE place: the `.env` file at the
     project root (with `.env.example` documenting every key).
  2. Validating types and constraints at startup, via Pydantic, instead of
     failing deep inside a pipeline run with a confusing TypeError.
  3. Resolving every path to an absolute path rooted at the project
     directory, so the app behaves identically regardless of the working
     directory it's launched from (a `streamlit run` from a different cwd
     is a classic source of "file not found" bugs).
  4. Creating any missing output directories (logs/, indexes/, data/) up
     front, so downstream code can assume they exist.

HOW IT WORKS INTERNALLY
------------------------
`pydantic-settings.BaseSettings` is a Pydantic model whose field values are
populated, in priority order, from: (a) explicit constructor kwargs,
(b) environment variables, (c) a `.env` file, (d) field defaults. We only
ever rely on (b)/(c)/(d) here. Pydantic validates each field's type the
moment the class is instantiated — an invalid `CHUNK_SIZE=abc` in `.env`
fails immediately with a clear error, not three modules later.

`get_settings()` is wrapped in `functools.lru_cache` so the `.env` file is
parsed and validated exactly once per process, and every caller shares the
same `Settings` instance (a cheap, safe singleton — no global mutable state
beyond "read a file once").

TIME / MEMORY COMPLEXITY
-------------------------
O(1) relative to the rest of the pipeline: parsing a small `.env` file and
validating ~25 scalar fields is microseconds and a few KB, done once at
process startup. Not a performance-relevant module.

ADVANTAGES
-----------
- Single source of truth; new modules just import `settings`.
- Fails fast with readable errors on misconfiguration.
- Type-safe: no `int(os.environ["CHUNK_SIZE"])` scattered everywhere.
- Environment-independent paths (absolute, resolved at startup).

DISADVANTAGES
--------------
- A process-wide singleton makes it awkward to run two different
  configurations in the same Python process (e.g., in parallel tests) —
  you'd need to bypass the cache and construct `Settings(...)` directly.
- Changing `.env` requires a process restart; there's no hot-reload.

ALTERNATIVES CONSIDERED
-------------------------
- Plain `os.getenv()` calls: no validation, defaults duplicated everywhere.
- A YAML/TOML config file: fine too, but `.env` is the de-facto standard for
  secrets-adjacent local config and pairs naturally with `python-dotenv`.
- `dataclasses` + manual parsing: reinvents what Pydantic already does well.

BEST PRACTICES APPLIED
------------------------
- Secrets/environment-specific values never hardcoded — always overridable
  via `.env` or real environment variables (useful in Docker/CI later).
- Defaults are sane enough that the app runs with *zero* `.env` file.
- Paths are validated/resolved in one place instead of ad hoc `Path(...)`
  calls scattered through the codebase.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The project root is the `hybrid_rag/` directory: three levels up from this
# file (settings.py -> config/ -> app/ -> hybrid_rag/). Computing it from
# __file__ (rather than assuming the process cwd) is what makes every path
# in this file correct no matter where the app is launched from.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """All tunable configuration for the Hybrid RAG system.

    Every field maps 1:1 to an environment variable of the same name
    (uppercased). See `.env.example` for a documented list of every key.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Local LLM (Ollama) --------------------------------------------------
    llm_model: str = Field(
        default="llama3.2:3b",
        description="Ollama model tag used for answer generation. "
        "Must already be pulled locally via `ollama pull <name>`.",
    )
    ollama_base_url: str = Field(default="http://localhost:11434")
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1024, gt=0)

    # -- Embedding model (dense retrieval) -----------------------------------
    # Defaults to a small (~470MB) multilingual model rather than the
    # heavier BAAI/bge-m3 (~2.3GB) named in the original spec: bge-m3
    # caused severe swap-thrashing on this project's 8GB-RAM dev machine
    # (see app/retriever/embeddings.py's module docstring for the full
    # investigation). Swap to bge-m3 or intfloat/multilingual-e5-large in
    # .env on a machine with more RAM headroom (16GB+ recommended) for
    # better retrieval quality.
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        description="HuggingFace sentence-embedding model id. Must support "
        "Uzbek/multilingual text (e.g. BAAI/bge-m3, "
        "intfloat/multilingual-e5-large, or this lighter default).",
    )
    embedding_device: Literal["auto", "cpu", "cuda", "mps"] = "auto"

    # -- Reranker model (cross-encoder) --------------------------------------
    reranker_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    reranker_device: Literal["auto", "cpu", "cuda", "mps"] = "auto"

    # -- Chunking -------------------------------------------------------------
    chunk_size: int = Field(default=800, gt=0)
    chunk_overlap: int = Field(default=150, ge=0)
    chunking_strategy: Literal["character", "token"] = Field(
        default="character",
        description="How chunk_size/chunk_overlap are measured: raw "
        "characters, or an approximate whitespace/punctuation token count.",
    )

    # -- Retrieval --------------------------------------------------------------
    top_k: int = Field(
        default=20, gt=0, description="Candidates returned by EACH of dense/sparse search before fusion."
    )
    rerank_top_k: int = Field(
        default=5, gt=0, description="Final number of chunks kept after reranking, passed to the LLM."
    )
    dense_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    sparse_weight: float = Field(default=0.5, ge=0.0, le=1.0)

    # -- Query preprocessing & context compression ---------------------------------
    max_query_length: int = Field(
        default=1000, gt=0, description="Queries longer than this (characters) are truncated with a warning."
    )
    max_context_chars: int = Field(
        default=6000,
        gt=0,
        description="Total character budget across all chunks passed to the LLM after "
        "reranking; lowest-ranked chunks are dropped first if the reranked set exceeds it.",
    )
    context_similarity_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Word-set Jaccard similarity above which a lower-ranked chunk is "
        "considered redundant with an already-kept higher-ranked one (e.g. from "
        "CHUNK_OVERLAP between adjacent sub-chunks of the same article) and dropped.",
    )

    # -- Storage paths (raw strings from env; resolved to absolute Paths below) --
    vector_path: str = Field(default="indexes/faiss_index")
    bm25_path: str = Field(default="indexes/bm25_index.pkl")
    sqlite_path: str = Field(default="data/metadata.db")
    documents_path: str = Field(default="documents")
    log_dir: str = Field(default="logs")

    # -- Logging ------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @field_validator("chunk_overlap")
    @classmethod
    def _overlap_smaller_than_chunk(cls, v: int, info) -> int:
        chunk_size = info.data.get("chunk_size")
        if chunk_size is not None and v >= chunk_size:
            raise ValueError(f"chunk_overlap ({v}) must be smaller than chunk_size ({chunk_size})")
        return v

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "Settings":
        total = self.dense_weight + self.sparse_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"dense_weight + sparse_weight must equal 1.0, got {total}")
        return self

    # -- Resolved absolute paths (computed, not env-driven) ------------------
    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def vector_path_resolved(self) -> Path:
        return self._resolve(self.vector_path)

    @property
    def bm25_path_resolved(self) -> Path:
        return self._resolve(self.bm25_path)

    @property
    def sqlite_path_resolved(self) -> Path:
        return self._resolve(self.sqlite_path)

    @property
    def documents_path_resolved(self) -> Path:
        return self._resolve(self.documents_path)

    @property
    def log_dir_resolved(self) -> Path:
        return self._resolve(self.log_dir)

    def _resolve(self, relative_or_absolute: str) -> Path:
        p = Path(relative_or_absolute)
        return p if p.is_absolute() else (PROJECT_ROOT / p)

    def ensure_directories(self) -> None:
        """Create every output directory this config points to, if missing.

        Called once at process startup so downstream modules (indexer,
        SQLite connection, logger) can assume their target directory exists
        instead of each re-implementing `mkdir(parents=True, exist_ok=True)`.
        """
        for path in (
            self.vector_path_resolved.parent,
            self.bm25_path_resolved.parent,
            self.sqlite_path_resolved.parent,
            self.documents_path_resolved,
            self.log_dir_resolved,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings singleton, creating it on first call.

    `lru_cache(maxsize=1)` on a zero-argument function is a common, simple
    way to implement a lazily-initialized singleton in Python without a
    metaclass or module-level side effect at import time.
    """
    settings = Settings()
    settings.ensure_directories()
    return settings
