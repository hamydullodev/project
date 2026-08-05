"""
SQLite schema definition.

WHY THIS MODULE EXISTS
-----------------------
Keeping the DDL (`CREATE TABLE ...`) in one dedicated module, separate from
the code that *uses* the database (`repository.py`), means the schema can
be read, reviewed, and migrated independently of query logic. It's also the
one place that needs to change if we ever add a column.

SCHEMA DESIGN
--------------
Two tables, one relationship:

  documents (1) ----< (many) chunks

`documents` holds one row per ingested *file* — its identity (name, path,
type), a SHA-256 hash of its raw bytes (the mechanism that powers both
duplicate detection and incremental re-indexing — see repository.py), and
an indexing `status` so a crashed/partial ingestion is visible rather than
silently missing.

`chunks` holds one row per text chunk produced by the chunker (Milestone
4), each carrying exactly the metadata the spec requires: document name
(via the `documents` join, plus a denormalized `law_name` for fast
filtering), page number, section, article number, and a stable chunk id.
The chunk's `text` is stored here too — SQLite is the durable record of
"what text produced which embedding," which matters because FAISS and
BM25 (Milestones 6-7) are *rebuildable* from this table; they are caches
of it, not independent sources of truth.

`ON DELETE CASCADE` means deleting a document automatically deletes its
chunks in one statement — SQLite enforces this only when
`PRAGMA foreign_keys = ON` is set per-connection (see repository.py).

WHY DENORMALIZE `law_name` ONTO `chunks`
------------------------------------------
Strict 3NF would only store `law_name` on `documents` and require a JOIN
for every chunk query. We denormalize it onto `chunks` because almost
every read path in this app (retrieval results, the debug page, citations)
needs `law_name` alongside chunk text, and duplicating one short string per
chunk is a trivial storage cost against the ergonomic and performance
win of avoiding a JOIN on the hot path.

INDEXES
--------
- `documents.file_hash` (UNIQUE): the primary dedup mechanism — an insert
  of a byte-identical file is rejected by the DB itself, not just by
  application logic, so the invariant holds even under concurrent access.
- `documents.file_path`, `documents.status`, `chunks.document_id`,
  `chunks.law_name`, `chunks.article_number`: support the query patterns
  the app actually needs (find a document by its source path during
  incremental indexing, list pending docs, fetch a doc's chunks, filter
  by law/article on the debug and statistics pages) in O(log n) instead
  of a full table scan.
"""

from __future__ import annotations

DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id                  TEXT PRIMARY KEY,
    file_name           TEXT NOT NULL,
    file_path           TEXT NOT NULL,
    file_type           TEXT NOT NULL,              -- pdf | docx | txt | html
    law_name            TEXT,
    collection_id        TEXT,                        -- e.g. "jinoyat_kodeksi" — derived from folder, see app/config/collections.py
    collection_category  TEXT,                        -- e.g. "kodekslar" | "qonunlar" | "konstitutsiya" | "other"
    collection_title     TEXT,                        -- human-readable display title for collection_id
    file_hash           TEXT NOT NULL UNIQUE,        -- sha256(raw bytes) — dedup + change detection
    file_size_bytes     INTEGER NOT NULL,
    num_chunks          INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'pending',  -- pending | indexed | failed
    error_message       TEXT,
    created_at          TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);
"""

CHUNKS_TABLE = """
CREATE TABLE IF NOT EXISTS chunks (
    id                  TEXT PRIMARY KEY,              -- f"{document_id}::{chunk_index:05d}"
    document_id          TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index          INTEGER NOT NULL,               -- 0-based position within the document
    text                TEXT NOT NULL,
    char_count           INTEGER NOT NULL,
    law_name            TEXT,
    collection_id        TEXT,                            -- denormalized from documents, same rationale as law_name
    collection_category  TEXT,
    collection_title     TEXT,
    article_number       TEXT,
    section              TEXT,                            -- e.g. "I BO'LIM > 1-BOB"
    page_number           INTEGER,
    created_at            TEXT NOT NULL
);
"""

INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);",
    "CREATE INDEX IF NOT EXISTS idx_documents_file_path ON documents(file_path);",
    "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);",
    "CREATE INDEX IF NOT EXISTS idx_documents_collection_id ON documents(collection_id);",
    "CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);",
    "CREATE INDEX IF NOT EXISTS idx_chunks_law_name ON chunks(law_name);",
    "CREATE INDEX IF NOT EXISTS idx_chunks_article_number ON chunks(article_number);",
    "CREATE INDEX IF NOT EXISTS idx_chunks_collection_id ON chunks(collection_id);",
]

TABLES = [DOCUMENTS_TABLE, CHUNKS_TABLE]
ALL_STATEMENTS = [*TABLES, *INDEXES]

# Columns added after the initial release of this schema. `init_schema()`
# in repository.py applies these via `ALTER TABLE ... ADD COLUMN` for any
# already-existing database that predates them — `CREATE TABLE IF NOT
# EXISTS` above only helps brand-new databases, not upgrading existing ones.
MIGRATIONS: list[tuple[str, str, str]] = [
    # (table, column, full "ADD COLUMN" fragment)
    ("documents", "collection_id", "collection_id TEXT"),
    ("documents", "collection_category", "collection_category TEXT"),
    ("documents", "collection_title", "collection_title TEXT"),
    ("chunks", "collection_id", "collection_id TEXT"),
    ("chunks", "collection_category", "collection_category TEXT"),
    ("chunks", "collection_title", "collection_title TEXT"),
]
