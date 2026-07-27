"""
Typed Python representations of the `documents` and `chunks` rows.

WHY THIS MODULE EXISTS
-----------------------
`sqlite3.Row` objects are dict-like but untyped: `row["law_naem"]` (a typo)
fails silently at read time or returns `None` deep inside a template, far
from where the bug actually is. Wrapping every row in a Pydantic model
gives us autocomplete, type checking, and validation at the boundary where
data crosses from the database into the rest of the app — the same
rationale as `app/config/settings.py`.

These models are also what the ingestion pipeline (Milestone 10) will
construct *before* insertion, so `DocumentRecord`/`ChunkRecord` are the
single shared shape used on both the write path and the read path.

DESIGN NOTE: plain dataclasses vs. Pydantic
---------------------------------------------
We use Pydantic (not `@dataclass`) even though there's no external input
being parsed here, purely for consistency with the rest of the codebase
and because `model_dump()` gives us a free, correct dict-for-`sqlite3`
conversion without hand-writing `asdict()`-style boilerplate.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

DocumentStatus = Literal["pending", "indexed", "failed"]


def utc_now_iso() -> str:
    """ISO-8601 UTC timestamp, used for every created_at/updated_at column.

    Stored as TEXT (SQLite has no native datetime type) in a sortable,
    unambiguous format — always UTC, so there's no timezone-offset bugs
    when comparing timestamps written from different machines.
    """
    return datetime.now(timezone.utc).isoformat()


class DocumentRecord(BaseModel):
    """One row of the `documents` table: a single ingested source file."""

    id: str
    file_name: str
    file_path: str
    file_type: str  # "pdf" | "docx" | "txt" | "html"
    law_name: Optional[str] = None
    file_hash: str
    file_size_bytes: int
    num_chunks: int = 0
    status: DocumentStatus = "pending"
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "DocumentRecord":
        return cls(**dict(row))


class ChunkRecord(BaseModel):
    """One row of the `chunks` table: a single retrievable text chunk.

    Carries exactly the metadata fields the spec requires: document
    identity (via `document_id` + denormalized `law_name`), page number,
    section, article number, and a globally-unique, deterministic chunk id
    (`{document_id}::{chunk_index:05d}`) that FAISS and BM25 use as their
    shared key back into this table.
    """

    id: str
    document_id: str
    chunk_index: int
    text: str
    char_count: int
    law_name: Optional[str] = None
    article_number: Optional[str] = None
    section: Optional[str] = None
    page_number: Optional[int] = None
    created_at: str = Field(default_factory=utc_now_iso)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ChunkRecord":
        return cls(**dict(row))

    @staticmethod
    def make_id(document_id: str, chunk_index: int) -> str:
        return f"{document_id}::{chunk_index:05d}"
