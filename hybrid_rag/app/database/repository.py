"""
SQLite-backed repository for document and chunk metadata.

WHY THIS MODULE EXISTS
-----------------------
Every other module that needs to read or write document/chunk metadata
(the ingestion pipeline, the retriever, every Streamlit page) should never
write raw SQL itself — that scatters query logic across the codebase,
duplicates `PRAGMA` setup, and makes it easy to forget the
`foreign_keys = ON` pragma (SQLite has cascade deletes *disabled by
default* for backward compatibility, which surprises people). Instead,
every caller goes through `MetadataRepository`, a thin Repository-pattern
wrapper: one class, one connection policy, one place that knows SQL.

This is also where SQLite becomes the **source of truth**: the FAISS index
(Milestone 6) and BM25 index (Milestone 7) are derived, rebuildable caches
keyed by `chunk.id`. If either is lost or corrupted, `get_all_chunks()` is
enough to rebuild them from scratch — this repository is the one thing
that must never silently lose data.

HOW IT WORKS INTERNALLY
------------------------
Rather than holding one long-lived `sqlite3.Connection` for the process
lifetime, `_connect()` is a context manager that opens a connection, yields
it, and closes it on exit — one connection per unit of work. This trades a
small per-call connection-open cost (a few hundred microseconds against a
local file — irrelevant here) for a big correctness win: SQLite
connections are not safe to share across threads by default, and
Streamlit reruns application code on every user interaction, often from
different threads in its execution model. Short-lived, function-scoped
connections sidestep that entirely instead of requiring a
`check_same_thread=False` escape hatch and manual locking.

Every connection:
  - sets `row_factory = sqlite3.Row` so query results are dict-like
    (`row["law_name"]`) and can be unpacked straight into our Pydantic
    models via `**dict(row)`;
  - enables `PRAGMA foreign_keys = ON`, which is what makes
    `ON DELETE CASCADE` (declared in schema.py) actually delete a
    document's chunks when the document is deleted;
  - enables `PRAGMA journal_mode = WAL`, which lets reads and writes
    proceed concurrently instead of blocking each other — relevant once
    the Streamlit UI, the indexing pipeline, and (later) evaluation
    scripts might touch the DB around the same time.

TIME / MEMORY COMPLEXITY
-------------------------
- `upsert_document`, `get_document`, `get_chunk`: O(log n) via the primary
  key / unique index lookups declared in schema.py.
- `replace_chunks`: O(k) for k chunks in the document (delete-by-index scan
  + bulk insert via `executemany`).
- `get_all_chunks`: O(n) full table scan, O(n) memory — used only to
  rebuild FAISS/BM25 from scratch, which is inherently an O(n) operation
  anyway (every chunk must be re-embedded / re-tokenized).
- `get_statistics`: O(n) (aggregates computed in SQL, not Python, so the
  actual scan happens inside SQLite's C implementation, not the GIL).

ADVANTAGES
-----------
- Cascade deletes keep `chunks` from ever orphaning when a document is
  removed — a common source of "ghost search results" bugs if handled
  manually in application code instead of by the DB.
- Repository pattern means every other module has ZERO SQL in it — the
  ingestion pipeline just calls `repo.upsert_document(...)`.
- SQLite is a single file, zero-config, and requires no separate server
  process — a good fit for "fully local, single user" per the project
  requirements.

DISADVANTAGES
--------------
- SQLite handles concurrent *writers* poorly compared to a client-server
  DB (Postgres, etc.) — fine here because this is a single-user local app,
  but would need to change for multi-user deployment.
- Opening a new connection per call has overhead that would matter under
  high query-per-second load; irrelevant at the scale of a personal legal
  corpus (thousands, not millions, of chunks).

ALTERNATIVES CONSIDERED
-------------------------
- A long-lived module-level connection: simpler code, but reintroduces the
  thread-safety problem Streamlit's execution model creates.
- An ORM (SQLAlchemy): more powerful, but adds a dependency and an
  abstraction layer this project's needs (two tables, ~10 query patterns)
  don't justify — raw SQL is easier to read top-to-bottom here.

BEST PRACTICES APPLIED
------------------------
- Parameterized queries everywhere (`?` placeholders) — never string
  interpolation — which eliminates SQL injection risk even though this app
  has no untrusted external users today.
- Every write operation logs at INFO (or ERROR on failure), satisfying the
  "log everything" requirement for the ingestion pipeline.
- `commit()` is only ever called on the happy path; an exception inside
  the `with` block leaves the transaction uncommitted and the connection
  is closed without committing, so a crash mid-write can't leave the DB in
  a half-written state for a single logical operation.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel

from app.config import settings
from app.database.models import ChunkRecord, DocumentRecord, utc_now_iso
from app.database.schema import INDEXES, MIGRATIONS, TABLES
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CollectionSummary(BaseModel):
    """One row of the "Browse Laws" collection listing: `GET /api/collections`."""

    collection_id: str
    category: str | None
    title: str | None
    num_documents: int
    num_chunks: int
    source_url: str | None = None


class MetadataRepository:
    """CRUD + query access to the `documents` and `chunks` tables."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.sqlite_path_resolved
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    # -- connection management ------------------------------------------------

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Create tables if they don't already exist, apply column
        migrations for tables that predate those columns, THEN create
        indexes — in that order, because an index on a column that a
        pre-existing table doesn't have yet would fail (`CREATE TABLE IF
        NOT EXISTS` only helps brand-new databases; migrations must run
        before any index referencing a migrated column). Idempotent
        either way.
        """
        with self._connect() as conn:
            for statement in TABLES:
                conn.execute(statement)
            for table, column, add_column_fragment in MIGRATIONS:
                existing_columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table});")}
                if column not in existing_columns:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {add_column_fragment};")
                    logger.info("Migrated schema: added %s.%s", table, column)
            for statement in INDEXES:
                conn.execute(statement)
            conn.commit()
        logger.debug("Schema ensured at %s", self.db_path)

    # -- documents --------------------------------------------------------------

    def get_document_by_hash(self, file_hash: str) -> DocumentRecord | None:
        """Look up a document by content hash — the dedup entry point.

        The ingestion pipeline calls this before parsing/chunking a file:
        if a document with an identical hash already exists, ingestion is
        skipped entirely (see Milestone 10).
        """
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE file_hash = ?;", (file_hash,)).fetchone()
        return DocumentRecord.from_row(row) if row else None

    def get_document(self, document_id: str) -> DocumentRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?;", (document_id,)).fetchone()
        return DocumentRecord.from_row(row) if row else None

    def get_document_by_path(self, file_path: str) -> DocumentRecord | None:
        """Look up a document by source file path — the incremental-
        indexing entry point (Milestone 10): "is this file already
        tracked, and if so, under which document_id?" lets a changed
        file be re-indexed IN PLACE (same document_id, replacing its old
        chunks) rather than as a brand-new document that orphans the old
        one's chunks and vectors.
        """
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE file_path = ?;", (file_path,)).fetchone()
        return DocumentRecord.from_row(row) if row else None

    def list_documents(self, status: str | None = None) -> list[DocumentRecord]:
        with self._connect() as conn:
            if status is None:
                rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC;").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM documents WHERE status = ? ORDER BY created_at DESC;",
                    (status,),
                ).fetchall()
        return [DocumentRecord.from_row(r) for r in rows]

    def upsert_document(self, doc: DocumentRecord) -> None:
        """Insert a new document row, or overwrite an existing one by id.

        Used both for the initial "pending" row created before parsing,
        and to update status/num_chunks after chunking completes.
        """
        doc.updated_at = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents
                    (id, file_name, file_path, file_type, law_name,
                     collection_id, collection_category, collection_title, file_hash,
                     file_size_bytes, num_chunks, status, error_message,
                     created_at, updated_at)
                VALUES (:id, :file_name, :file_path, :file_type, :law_name,
                        :collection_id, :collection_category, :collection_title, :file_hash,
                        :file_size_bytes, :num_chunks, :status, :error_message,
                        :created_at, :updated_at)
                ON CONFLICT(id) DO UPDATE SET
                    file_name=excluded.file_name,
                    file_path=excluded.file_path,
                    file_type=excluded.file_type,
                    law_name=excluded.law_name,
                    collection_id=excluded.collection_id,
                    collection_category=excluded.collection_category,
                    collection_title=excluded.collection_title,
                    file_hash=excluded.file_hash,
                    file_size_bytes=excluded.file_size_bytes,
                    num_chunks=excluded.num_chunks,
                    status=excluded.status,
                    error_message=excluded.error_message,
                    updated_at=excluded.updated_at;
                """,
                doc.model_dump(),
            )
            conn.commit()
        logger.info("Upserted document id=%s file=%s status=%s", doc.id, doc.file_name, doc.status)

    def delete_document(self, document_id: str) -> None:
        """Delete a document and (via ON DELETE CASCADE) all its chunks."""
        with self._connect() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?;", (document_id,))
            conn.commit()
        logger.info("Deleted document id=%s (chunks cascade-deleted)", document_id)

    def delete_all(self) -> None:
        """Wipe both tables. Used by the UI's 'Delete Index' action."""
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks;")
            conn.execute("DELETE FROM documents;")
            conn.commit()
        logger.warning("Deleted ALL documents and chunks from metadata store")

    # -- chunks -------------------------------------------------------------------

    def replace_chunks(self, document_id: str, chunks: list[ChunkRecord]) -> None:
        """Atomically replace all chunks belonging to `document_id`.

        Used both for first-time indexing (no prior chunks to delete — the
        DELETE is a no-op) and for incremental re-indexing of a changed
        file (old chunks for stale content must not linger and pollute
        search results).
        """
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?;", (document_id,))
            conn.executemany(
                """
                INSERT INTO chunks
                    (id, document_id, chunk_index, text, char_count,
                     law_name, collection_id, collection_category, collection_title,
                     article_number, section, page_number, created_at)
                VALUES (:id, :document_id, :chunk_index, :text, :char_count,
                        :law_name, :collection_id, :collection_category, :collection_title,
                        :article_number, :section, :page_number, :created_at)
                """,
                [c.model_dump() for c in chunks],
            )
            conn.execute(
                "UPDATE documents SET num_chunks = ?, updated_at = ? WHERE id = ?;",
                (len(chunks), utc_now_iso(), document_id),
            )
            conn.commit()
        logger.info("Replaced chunks for document_id=%s count=%d", document_id, len(chunks))

    def get_chunks_for_document(self, document_id: str) -> list[ChunkRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC;",
                (document_id,),
            ).fetchall()
        return [ChunkRecord.from_row(r) for r in rows]

    def get_chunk(self, chunk_id: str) -> ChunkRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM chunks WHERE id = ?;", (chunk_id,)).fetchone()
        return ChunkRecord.from_row(row) if row else None

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[ChunkRecord]:
        """Batch-fetch chunks by id, preserving no particular order.

        Used by the retriever to hydrate FAISS/BM25 hit ids (which carry
        no metadata of their own) back into full `ChunkRecord`s.
        """
        if not chunk_ids:
            return []
        placeholders = ",".join("?" for _ in chunk_ids)
        with self._connect() as conn:
            rows = conn.execute(f"SELECT * FROM chunks WHERE id IN ({placeholders});", chunk_ids).fetchall()
        return [ChunkRecord.from_row(r) for r in rows]

    def get_all_chunks(self) -> list[ChunkRecord]:
        """Return every chunk in the store — the input to a full index rebuild."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM chunks ORDER BY id ASC;").fetchall()
        return [ChunkRecord.from_row(r) for r in rows]

    def get_collections(self) -> list[CollectionSummary]:
        """List every distinct collection with its document/chunk counts.

        Drives `GET /api/collections` (the "Browse Laws" picker) and any
        UI needing a list of scopeable law codes. Aggregation happens in
        SQL, same rationale as `get_statistics()`.
        """
        from app.config.collections import SOURCE_URLS

        with self._connect() as conn:
            doc_rows = conn.execute(
                """
                SELECT collection_id, collection_category, collection_title, COUNT(*) AS n
                FROM documents
                WHERE collection_id IS NOT NULL
                GROUP BY collection_id;
                """
            ).fetchall()
            chunk_rows = conn.execute(
                """
                SELECT collection_id, COUNT(*) AS n
                FROM chunks
                WHERE collection_id IS NOT NULL
                GROUP BY collection_id;
                """
            ).fetchall()

        chunk_counts = {row["collection_id"]: row["n"] for row in chunk_rows}
        summaries = [
            CollectionSummary(
                collection_id=row["collection_id"],
                category=row["collection_category"],
                title=row["collection_title"],
                num_documents=row["n"],
                num_chunks=chunk_counts.get(row["collection_id"], 0),
                source_url=SOURCE_URLS.get(row["collection_id"]),
            )
            for row in doc_rows
        ]
        summaries.sort(key=lambda s: (s.category or "", s.title or s.collection_id))
        return summaries

    # -- aggregate stats (drives the Statistics page, Milestone 19) -----------------

    def count_documents(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM documents;").fetchone()[0]

    def count_chunks(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM chunks;").fetchone()[0]

    def get_statistics(self) -> dict:
        """Aggregate counts used by the Statistics page.

        All aggregation happens in SQL (COUNT/AVG/SUM) rather than by
        loading every row into Python and reducing there — for a corpus of
        any real size this is both faster and far lower memory.
        """
        with self._connect() as conn:
            doc_count = conn.execute("SELECT COUNT(*) FROM documents;").fetchone()[0]
            chunk_count = conn.execute("SELECT COUNT(*) FROM chunks;").fetchone()[0]
            avg_chunk_chars = conn.execute("SELECT AVG(char_count) FROM chunks;").fetchone()[0]
            # Grouped by collection_title (folder-derived, reliable) rather
            # than the raw law_name (free text parsed from document
            # content) — law_name is inconsistent across documents (some
            # extract a generic phrase like "Oʻzbekiston Respublikasining
            # Qonuni" instead of the specific law title), which used to
            # collapse dozens of distinct laws into one misleading bucket
            # here. Falls back to law_name/'Unknown' only for any legacy
            # rows indexed before collection_id existed.
            by_law = conn.execute("""
                SELECT COALESCE(collection_title, law_name, 'Unknown') AS law_name, COUNT(*) AS chunk_count
                FROM chunks GROUP BY COALESCE(collection_title, law_name, 'Unknown') ORDER BY chunk_count DESC;
                """).fetchall()
            by_status = conn.execute(
                "SELECT status, COUNT(*) AS n FROM documents GROUP BY status;"
            ).fetchall()

        db_size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "avg_chunk_size_chars": round(avg_chunk_chars, 1) if avg_chunk_chars else 0.0,
            "chunks_by_law": {row["law_name"]: row["chunk_count"] for row in by_law},
            "documents_by_status": {row["status"]: row["n"] for row in by_status},
            "db_size_bytes": db_size_bytes,
        }
