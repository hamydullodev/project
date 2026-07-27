"""
Unit tests for app.database (schema + repository).

Each test uses a fresh SQLite file inside pytest's `tmp_path` fixture, so
tests never touch the real `data/metadata.db` and never interfere with
each other — a new, empty database is created and destroyed per test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.database import ChunkRecord, DocumentRecord, MetadataRepository


@pytest.fixture()
def repo(tmp_path: Path) -> MetadataRepository:
    return MetadataRepository(db_path=tmp_path / "test_metadata.db")


def _make_document(doc_id: str = "doc-1", file_hash: str = "hash-1") -> DocumentRecord:
    return DocumentRecord(
        id=doc_id,
        file_name="fuqorolik.txt",
        file_path="/documents/raw/fuqorolik.txt",
        file_type="txt",
        law_name="Fuqarolik kodeksi",
        file_hash=file_hash,
        file_size_bytes=1024,
        status="pending",
    )


def _make_chunks(doc_id: str, n: int) -> list[ChunkRecord]:
    return [
        ChunkRecord(
            id=ChunkRecord.make_id(doc_id, i),
            document_id=doc_id,
            chunk_index=i,
            text=f"1-modda. Text of chunk {i}",
            char_count=len(f"1-modda. Text of chunk {i}"),
            law_name="Fuqarolik kodeksi",
            article_number="1",
            section="I BO'LIM",
            page_number=1,
        )
        for i in range(n)
    ]


def test_schema_created_on_init(repo: MetadataRepository):
    assert repo.db_path.exists()
    assert repo.count_documents() == 0
    assert repo.count_chunks() == 0


def test_upsert_and_get_document(repo: MetadataRepository):
    doc = _make_document()
    repo.upsert_document(doc)

    fetched = repo.get_document("doc-1")
    assert fetched is not None
    assert fetched.file_name == "fuqorolik.txt"
    assert fetched.status == "pending"

    # Upsert again with a changed status -> should overwrite, not duplicate.
    doc.status = "indexed"
    repo.upsert_document(doc)
    assert repo.count_documents() == 1
    assert repo.get_document("doc-1").status == "indexed"


def test_duplicate_file_hash_detected(repo: MetadataRepository):
    doc = _make_document()
    repo.upsert_document(doc)

    found = repo.get_document_by_hash("hash-1")
    assert found is not None
    assert found.id == "doc-1"

    assert repo.get_document_by_hash("nonexistent-hash") is None


def test_duplicate_hash_insert_raises(repo: MetadataRepository):
    """The UNIQUE constraint on file_hash is the DB-level dedup guarantee —
    inserting two different documents with the same hash must fail even if
    application logic forgets to check first."""
    import sqlite3

    repo.upsert_document(_make_document(doc_id="doc-1", file_hash="same-hash"))
    with pytest.raises(sqlite3.IntegrityError):
        repo.upsert_document(_make_document(doc_id="doc-2", file_hash="same-hash"))


def test_replace_chunks_and_fetch(repo: MetadataRepository):
    repo.upsert_document(_make_document())
    chunks = _make_chunks("doc-1", n=5)
    repo.replace_chunks("doc-1", chunks)

    assert repo.count_chunks() == 5
    fetched = repo.get_chunks_for_document("doc-1")
    assert [c.chunk_index for c in fetched] == [0, 1, 2, 3, 4]
    assert repo.get_document("doc-1").num_chunks == 5


def test_replace_chunks_is_idempotent_on_reindex(repo: MetadataRepository):
    """Re-indexing a changed file must not leave stale chunks behind."""
    repo.upsert_document(_make_document())
    repo.replace_chunks("doc-1", _make_chunks("doc-1", n=5))
    repo.replace_chunks("doc-1", _make_chunks("doc-1", n=2))  # file shrank

    assert repo.count_chunks() == 2
    assert repo.get_document("doc-1").num_chunks == 2


def test_cascade_delete_removes_chunks(repo: MetadataRepository):
    repo.upsert_document(_make_document())
    repo.replace_chunks("doc-1", _make_chunks("doc-1", n=3))
    assert repo.count_chunks() == 3

    repo.delete_document("doc-1")

    assert repo.count_documents() == 0
    assert repo.count_chunks() == 0  # cascade must have removed orphans
    assert repo.get_chunks_for_document("doc-1") == []


def test_get_chunks_by_ids(repo: MetadataRepository):
    repo.upsert_document(_make_document())
    chunks = _make_chunks("doc-1", n=4)
    repo.replace_chunks("doc-1", chunks)

    wanted_ids = [chunks[0].id, chunks[2].id]
    fetched = repo.get_chunks_by_ids(wanted_ids)
    assert {c.id for c in fetched} == set(wanted_ids)


def test_statistics(repo: MetadataRepository):
    repo.upsert_document(_make_document(doc_id="doc-1", file_hash="h1"))
    repo.replace_chunks("doc-1", _make_chunks("doc-1", n=3))

    stats = repo.get_statistics()
    assert stats["total_documents"] == 1
    assert stats["total_chunks"] == 3
    assert stats["avg_chunk_size_chars"] > 0
    assert "Fuqarolik kodeksi" in stats["chunks_by_law"]


def test_delete_all_wipes_everything(repo: MetadataRepository):
    repo.upsert_document(_make_document())
    repo.replace_chunks("doc-1", _make_chunks("doc-1", n=3))

    repo.delete_all()

    assert repo.count_documents() == 0
    assert repo.count_chunks() == 0
