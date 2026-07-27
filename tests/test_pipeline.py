"""
Unit tests for app.ingestion.pipeline.IndexingPipeline.

Every test constructs its own MetadataRepository/FAISSVectorStore/
BM25SparseIndex scoped to pytest's tmp_path, and passes them explicitly
into IndexingPipeline(...) — never relying on the constructor's defaults,
which point at the real project's data/indexes directories. This is the
one thing every test here must get right, or a test run would corrupt
this project's actual index.

Uses the real (small) embedding model, since embedding is central to what
this pipeline does — a fake/mocked embedder would test very little of
real value here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.database import MetadataRepository
from app.ingestion.pipeline import IndexingPipeline
from app.retriever import BM25SparseIndex, EmbeddingModel, FAISSVectorStore

SMALL_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

SAMPLE_LAW_A = """\
TEST RESPUBLIKASINING SINOV KODEKSI
1-BOB.
UMUMIY QOIDALAR
1-modda. Birinchi modda
Bu birinchi moddaning matni fuqarolik huquqi toʻgʻrisida.
2-modda. Ikkinchi modda
Bu ikkinchi moddaning matni mehnat huquqi toʻgʻrisida.
"""

SAMPLE_LAW_A_MODIFIED = """\
TEST RESPUBLIKASINING SINOV KODEKSI
1-BOB.
UMUMIY QOIDALAR
1-modda. Birinchi modda
Bu birinchi moddaning YANGILANGAN matni fuqarolik huquqi toʻgʻrisida.
"""

SAMPLE_LAW_B = """\
IKKINCHI RESPUBLIKASINING KODEKSI
1-BOB.
BOSHQA QOIDALAR
1-modda. Boshqa modda
Bu boshqa moddaning matni jinoyat huquqi toʻgʻrisida.
"""


@pytest.fixture(scope="module")
def embedding_model() -> EmbeddingModel:
    return EmbeddingModel(model_name=SMALL_MODEL, device="cpu")


@pytest.fixture()
def pipeline_factory(tmp_path: Path, embedding_model: EmbeddingModel):
    """Returns a function that builds a fresh, tmp_path-scoped IndexingPipeline.

    Each call creates NEW repo/vector_store/bm25_index instances (unless
    told to reuse existing ones), so tests can simulate "restart the
    pipeline" (e.g. to test loading previously-saved indexes) explicitly.
    """
    counter = {"n": 0}

    def _make(reuse_paths: bool = True):
        counter["n"] += 1
        suffix = "" if reuse_paths else f"_{counter['n']}"
        db_path = tmp_path / f"test{suffix}.db"
        vector_path = tmp_path / f"test_vectors{suffix}"
        bm25_path = tmp_path / f"test_bm25{suffix}.pkl"

        repo = MetadataRepository(db_path=db_path)
        # Explicit `path=` is essential here: FAISSVectorStore/BM25SparseIndex
        # remember the path they're given and use it as save()'s default
        # target. Without it, IndexingPipeline._save_indexes() (which calls
        # save() with no arguments) would fall back to the real project's
        # settings.vector_path_resolved / bm25_path_resolved and silently
        # write test data into the actual indexes/ directory.
        vector_store = FAISSVectorStore(dimension=embedding_model.dimension, path=vector_path)
        bm25_index = BM25SparseIndex(path=bm25_path)

        pipeline = IndexingPipeline(
            repo=repo,
            embedding_model=embedding_model,
            vector_store=vector_store,
            bm25_index=bm25_index,
        )
        pipeline._paths = (db_path, vector_path, bm25_path)  # stash for reload tests
        return pipeline

    return _make


@pytest.fixture()
def docs_dir(tmp_path: Path) -> Path:
    d = tmp_path / "documents"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# first-time indexing
# ---------------------------------------------------------------------------


def test_sync_indexes_new_files(pipeline_factory, docs_dir: Path):
    (docs_dir / "law_a.txt").write_text(SAMPLE_LAW_A, encoding="utf-8")
    (docs_dir / "law_b.txt").write_text(SAMPLE_LAW_B, encoding="utf-8")

    pipeline = pipeline_factory()
    summary = pipeline.sync(docs_dir)

    assert summary.total_files_scanned == 2
    assert summary.total_indexed == 2
    assert summary.total_failed == 0
    assert summary.total_chunks_in_index > 0
    assert len(pipeline.vector_store) == summary.total_chunks_in_index
    assert len(pipeline.bm25_index) == summary.total_chunks_in_index
    assert pipeline.repo.count_documents() == 2


def test_sync_ignores_unsupported_file_types(pipeline_factory, docs_dir: Path):
    (docs_dir / "law_a.txt").write_text(SAMPLE_LAW_A, encoding="utf-8")
    (docs_dir / "readme.md").write_text("not a legal document", encoding="utf-8")
    (docs_dir / ".gitkeep").write_text("", encoding="utf-8")

    pipeline = pipeline_factory()
    summary = pipeline.sync(docs_dir)

    assert summary.total_files_scanned == 1  # only law_a.txt


# ---------------------------------------------------------------------------
# incremental behavior: unchanged files skip
# ---------------------------------------------------------------------------


def test_sync_twice_skips_unchanged_files(pipeline_factory, docs_dir: Path):
    (docs_dir / "law_a.txt").write_text(SAMPLE_LAW_A, encoding="utf-8")

    pipeline = pipeline_factory()
    first = pipeline.sync(docs_dir)
    second = pipeline.sync(docs_dir)

    assert first.total_indexed == 1
    assert second.total_indexed == 0
    assert second.total_skipped_unchanged == 1
    assert second.total_chunks_in_index == first.total_chunks_in_index


# ---------------------------------------------------------------------------
# incremental behavior: changed file re-indexed in place
# ---------------------------------------------------------------------------


def test_changed_file_reindexed_in_place(pipeline_factory, docs_dir: Path):
    path = docs_dir / "law_a.txt"
    path.write_text(SAMPLE_LAW_A, encoding="utf-8")

    pipeline = pipeline_factory()
    first = pipeline.sync(docs_dir)
    original_doc_id = first.outcomes[0].document_id
    original_chunk_count = first.total_chunks_in_index

    path.write_text(SAMPLE_LAW_A_MODIFIED, encoding="utf-8")  # now has 1 article, not 2
    second = pipeline.sync(docs_dir)

    assert second.total_indexed == 1
    assert second.outcomes[0].document_id == original_doc_id  # same identity, not a new doc
    assert pipeline.repo.count_documents() == 1  # not 2 - updated in place

    # The modified file has fewer articles -> fewer chunks; the vector
    # index must not retain stale vectors from the old, longer version.
    assert second.total_chunks_in_index < original_chunk_count
    assert len(pipeline.vector_store) == second.total_chunks_in_index


def test_changed_file_content_is_searchable_after_reindex(pipeline_factory, docs_dir: Path):
    """Verified via SQLite (not BM25 search): after this edit the corpus
    has only 1 chunk total, and with a single-document corpus every term
    gets a non-positive BM25 IDF by design (see bm25_index.py's
    docstring and the edge case documented in tests/test_bm25_index.py)
    - checking the stored chunk text directly is both more direct and
    sidesteps that unrelated degenerate case entirely."""
    path = docs_dir / "law_a.txt"
    path.write_text(SAMPLE_LAW_A, encoding="utf-8")

    pipeline = pipeline_factory()
    pipeline.sync(docs_dir)

    path.write_text(SAMPLE_LAW_A_MODIFIED, encoding="utf-8")
    pipeline.sync(docs_dir)

    all_chunks = pipeline.repo.get_all_chunks()
    assert any("YANGILANGAN" in c.text for c in all_chunks)
    assert not any("Ikkinchi modda" in c.text for c in all_chunks)  # old content is gone


# ---------------------------------------------------------------------------
# duplicate detection
# ---------------------------------------------------------------------------


def test_duplicate_content_under_different_name_is_skipped(pipeline_factory, docs_dir: Path):
    (docs_dir / "law_a.txt").write_text(SAMPLE_LAW_A, encoding="utf-8")
    (docs_dir / "law_a_copy.txt").write_text(SAMPLE_LAW_A, encoding="utf-8")  # byte-identical

    pipeline = pipeline_factory()
    summary = pipeline.sync(docs_dir)

    assert summary.total_indexed == 1
    assert summary.total_skipped_duplicate == 1
    assert pipeline.repo.count_documents() == 1


# ---------------------------------------------------------------------------
# broken files don't stop the batch
# ---------------------------------------------------------------------------


def test_empty_file_fails_gracefully_others_still_indexed(pipeline_factory, docs_dir: Path):
    (docs_dir / "law_a.txt").write_text(SAMPLE_LAW_A, encoding="utf-8")
    (docs_dir / "empty.txt").write_text("   \n  ", encoding="utf-8")

    pipeline = pipeline_factory()
    summary = pipeline.sync(docs_dir)

    assert summary.total_indexed == 1
    assert summary.total_failed == 1

    failed_outcome = next(o for o in summary.outcomes if o.status == "failed")
    assert "empty" in failed_outcome.file_path
    assert failed_outcome.error_message is not None

    failed_doc = pipeline.repo.get_document(failed_outcome.document_id)
    assert failed_doc.status == "failed"


# ---------------------------------------------------------------------------
# delete_all / rebuild / remove_document
# ---------------------------------------------------------------------------


def test_delete_all_wipes_everything(pipeline_factory, docs_dir: Path):
    (docs_dir / "law_a.txt").write_text(SAMPLE_LAW_A, encoding="utf-8")
    pipeline = pipeline_factory()
    pipeline.sync(docs_dir)
    assert pipeline.repo.count_documents() == 1

    pipeline.delete_all()

    assert pipeline.repo.count_documents() == 0
    assert pipeline.vector_store.is_empty
    assert pipeline.bm25_index.is_empty


def test_rebuild_reindexes_from_scratch(pipeline_factory, docs_dir: Path):
    (docs_dir / "law_a.txt").write_text(SAMPLE_LAW_A, encoding="utf-8")
    pipeline = pipeline_factory()
    first = pipeline.sync(docs_dir)

    summary = pipeline.rebuild(docs_dir)

    assert summary.total_indexed == 1  # reprocessed, not skipped
    assert summary.total_chunks_in_index == first.total_chunks_in_index


def test_remove_document_deletes_its_chunks_and_vectors(pipeline_factory, docs_dir: Path):
    (docs_dir / "law_a.txt").write_text(SAMPLE_LAW_A, encoding="utf-8")
    (docs_dir / "law_b.txt").write_text(SAMPLE_LAW_B, encoding="utf-8")

    pipeline = pipeline_factory()
    summary = pipeline.sync(docs_dir)
    doc_a_id = next(o.document_id for o in summary.outcomes if "law_a" in o.file_path)

    pipeline.remove_document(doc_a_id)

    assert pipeline.repo.get_document(doc_a_id) is None
    assert pipeline.repo.count_documents() == 1
    remaining_chunk_ids = {c.id for c in pipeline.repo.get_all_chunks()}
    assert all(cid.startswith(doc_a_id) is False for cid in remaining_chunk_ids)
    assert len(pipeline.bm25_index) == len(remaining_chunk_ids)


# ---------------------------------------------------------------------------
# corrupted/missing vector index self-heals
# ---------------------------------------------------------------------------


def test_empty_vector_store_with_existing_metadata_self_heals(
    pipeline_factory, docs_dir: Path, embedding_model, tmp_path: Path
):
    (docs_dir / "law_a.txt").write_text(SAMPLE_LAW_A, encoding="utf-8")

    pipeline = pipeline_factory()
    first = pipeline.sync(docs_dir)
    assert not pipeline.vector_store.is_empty

    # Simulate "FAISS index file was lost/corrupted": construct a fresh
    # IndexingPipeline reusing the SAME repo (metadata survives) but a
    # brand-new, empty FAISSVectorStore. Explicit tmp_path-scoped `path=`
    # on both, same reasoning as pipeline_factory above.
    fresh_vector_store = FAISSVectorStore(
        dimension=embedding_model.dimension, path=tmp_path / "healed_vectors"
    )
    healed_pipeline = IndexingPipeline(
        repo=pipeline.repo,
        embedding_model=embedding_model,
        vector_store=fresh_vector_store,
        bm25_index=BM25SparseIndex(path=tmp_path / "healed_bm25.pkl"),
    )
    assert healed_pipeline.vector_store.is_empty
    assert healed_pipeline.repo.count_chunks() > 0

    summary = healed_pipeline.sync(docs_dir)

    # Even though the file itself is UNCHANGED (same hash), vectors must
    # be repopulated because the index was empty.
    assert summary.total_indexed == 1
    assert summary.total_skipped_unchanged == 0
    assert len(healed_pipeline.vector_store) == first.total_chunks_in_index


# ---------------------------------------------------------------------------
# save/load round trip through the real persistence paths
# ---------------------------------------------------------------------------


def test_indexes_are_saved_and_reloadable(pipeline_factory, docs_dir: Path, tmp_path: Path, embedding_model):
    (docs_dir / "law_a.txt").write_text(SAMPLE_LAW_A, encoding="utf-8")

    vector_path = tmp_path / "saved_vectors"
    bm25_path = tmp_path / "saved_bm25.pkl"
    repo = MetadataRepository(db_path=tmp_path / "saved.db")
    pipeline = IndexingPipeline(
        repo=repo,
        embedding_model=embedding_model,
        vector_store=FAISSVectorStore(dimension=embedding_model.dimension, path=vector_path),
        bm25_index=BM25SparseIndex(path=bm25_path),
    )
    # sync() itself already writes to vector_path/bm25_path (via the
    # `path=` given above), so this call is exercising the real save
    # path, not a settings-default fallback.
    pipeline.sync(docs_dir)

    reloaded_vector_store = FAISSVectorStore.load(vector_path)
    reloaded_bm25 = BM25SparseIndex.load(bm25_path)

    assert len(reloaded_vector_store) == len(pipeline.vector_store)
    assert len(reloaded_bm25) == len(pipeline.bm25_index)
