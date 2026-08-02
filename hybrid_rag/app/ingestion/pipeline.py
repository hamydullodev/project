"""
Indexing pipeline orchestrator: ties every prior milestone into one flow.

WHY THIS MODULE EXISTS
-----------------------
Milestones 2-9 built independent, well-tested pieces: load a document,
clean it, chunk it, embed the chunks, store the vectors, store the lexical
index, store the metadata. None of those pieces know about each other —
by design, so each could be tested and reasoned about in isolation. This
module is where they compose into the actual operation a user triggers:
"index my documents." It implements exactly the flow the spec describes —
*load documents, extract text, clean text, normalize Unicode, remove
duplicates, split into chunks, create embeddings, store vectors, create
the BM25 index, store metadata, save everything locally* — as one
coherent `IndexingPipeline.sync()` call.

WHY THERE IS NO SEPARATE "incremental" FLAG
------------------------------------------------
An earlier design considered an `incremental: bool` parameter on `sync()`
("full rebuild" vs "incremental update"). It turned out unnecessary: every
document's identity is tracked by a content hash (`compute_sha256`,
Milestone 3's dedup mechanism) AND by its file path
(`MetadataRepository.get_document_by_path`, added in this milestone).
`sync()` is ALWAYS incremental by construction — an unchanged file is
always skipped, a changed or new file is always (re)processed — so
calling it repeatedly is naturally cheap and correct. "Full rebuild" is
then simply `delete_all()` followed by the exact same `sync()` call: with
an empty database, every file looks "new," and the identical code path
handles it. One well-tested code path instead of two subtly different
ones for what is, at its core, the same operation with different starting
state.

WHY A CHANGED FILE REUSES ITS document_id (RATHER THAN CREATING A NEW ONE)
------------------------------------------------------------------------------
When a tracked file's content changes, `sync()` looks it up by PATH
(`get_document_by_path`), not just by hash, and reuses that document's
existing `document_id` — updating its chunks and vectors in place — rather
than minting a fresh id and leaving the old chunks/vectors as orphaned
dead weight in SQLite and FAISS. Before writing the new chunks, the OLD
chunk ids for that document are explicitly removed from the FAISS index
(`vector_store.remove(...)`) — necessary because a file can shrink (fewer
chunks than before), and `FAISSVectorStore.add()`'s idempotent
remove-then-add behavior (Milestone 6) only replaces ids that are
actually passed to it again; a chunk index that no longer exists in the
new version of the file would otherwise linger in the vector index
forever, silently surfacing stale content in search results.

WHY THE BM25 INDEX IS REBUILT ONCE AT THE END, NOT PER-DOCUMENT
---------------------------------------------------------------------
BM25 (Milestone 7) has no incremental update — every rebuild is a full-
corpus operation. Rebuilding it after each individual document inside a
loop over N documents would cost O(N) full rebuilds, each itself O(corpus
size) — O(N × corpus size) total, quadratic in the number of documents
being processed in one `sync()` call. Instead, `sync()` processes every
changed/new document's SQLite rows and FAISS vectors first, and rebuilds
BM25 exactly ONCE at the end from `MetadataRepository.get_all_chunks()` —
O(corpus size) total, regardless of how many documents changed in this
call.

WHY A CORRUPTED OR MISSING FAISS INDEX SELF-HEALS ON THE NEXT sync()
--------------------------------------------------------------------------
If `FAISSVectorStore.load()` raises `VectorStoreError` (missing or
corrupted index files — Milestone 6), the pipeline starts from a fresh,
empty in-memory index rather than crashing (the spec's "gracefully handle
corrupted indexes" requirement). But an empty vector index combined with
SQLite still recording documents as `status="indexed"` would normally
make `sync()` skip those files entirely (their hash hasn't changed) —
silently leaving the index empty forever. `sync()` detects exactly this
situation (`vector_store.is_empty and repo.count_chunks() > 0`) and, for
each unchanged-by-hash document, re-embeds its ALREADY-STORED chunk text
straight from SQLite and re-adds those vectors — skipping the expensive
re-parse/re-chunk step entirely, since the chunk text itself was never
lost (SQLite is the durable source of truth; FAISS/BM25 are rebuildable
caches of it, as stated in `database/repository.py`'s docstring). BM25
needs no equivalent special case: it always fully rebuilds every call
regardless of any of this, so a corrupted/missing BM25 file self-heals on
the very next `sync()` for free.

TIME / MEMORY COMPLEXITY
-------------------------
Per `sync()` call: O(F) file-hash computations (F = files in the
documents directory, each O(file size) to hash — Milestone 3), plus for
each of the C changed/new documents, O(document size) to load/clean/chunk
it and O(chunks × embedding cost) to embed it, plus one O(total corpus
size) BM25 rebuild at the end. Memory is bounded by the largest single
document being processed (documents are handled one at a time, not all
loaded simultaneously) plus the full chunk-text corpus needed for the
final BM25 rebuild.

ADVANTAGES
-----------
- One method (`sync`) safely handles first-time indexing, incremental
  updates, and post-corruption recovery — a caller (a future "Build
  Index" or "Update Index" UI button) doesn't need to know or choose
  which situation it's in.
- No document is silently double-indexed: identity is tracked by both
  path (update-in-place) and content hash (skip exact duplicates under a
  different filename), covering both ways a "duplicate" can arise.
- One bad file (corrupted PDF, empty file, encoding failure) is caught,
  recorded with `status="failed"` and an error message, and does not stop
  the rest of the batch from being indexed — the spec's "gracefully
  handle broken input" requirement, now visible at the orchestration
  level, not just within `loaders.py`.

DISADVANTAGES
--------------
- `sync()` processes files sequentially, not in parallel — simpler and
  easier to reason about (and to keep log output readable), at the cost
  of not parallelizing I/O-bound loading or embedding across documents.
  Acceptable at this project's scale (a handful of legal codes plus
  whatever a user uploads); would need revisiting for a much larger
  corpus.
- A file deleted from the documents directory is NOT automatically
  removed from the index by `sync()` — deletion is a deliberate, explicit
  operation (`remove_document`), not an automatic side effect of a file
  going missing from disk (which could just as easily mean "temporarily
  unmounted drive" as "the user wants this deleted").

ALTERNATIVES CONSIDERED
-------------------------
- Watching the filesystem for changes (e.g. via `watchdog`) and
  re-indexing automatically: adds a background process and a dependency
  for a personal, on-demand-use application where an explicit "Update
  Index" button (Milestone 18) is simpler, more predictable, and matches
  how the rest of this project's UI is designed to work.
- Storing embeddings/vectors keyed by content hash instead of chunk id (so
  identical chunk text across different documents shares one vector):
  would save some embedding computation for a corpus with repeated
  boilerplate, but complicates the id scheme for a marginal gain at this
  project's corpus size; not pursued.

BEST PRACTICES APPLIED
------------------------
- Every stage logs at INFO (progress) or ERROR (per-file failure),
  satisfying "log ingestion, embedding creation... errors" from the spec.
- `IndexingSummary` gives a structured, complete account of what happened
  in one `sync()` call — exactly what a future "Build Index" page needs
  to render a result summary instead of just a bare "done."
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.config import derive_collection, settings
from app.database import ChunkRecord, DocumentRecord, MetadataRepository
from app.ingestion.chunker import chunk_document
from app.ingestion.exceptions import DocumentLoadError
from app.ingestion.loaders import SUPPORTED_EXTENSIONS, load_document
from app.retriever import (
    BM25IndexError,
    BM25SparseIndex,
    EmbeddingModel,
    FAISSVectorStore,
    VectorStoreError,
    get_default_embedding_model,
)
from app.utils.hashing import compute_sha256
from app.utils.logger import get_logger

logger = get_logger(__name__)

DocumentOutcomeStatus = Literal["indexed", "skipped_unchanged", "skipped_duplicate", "failed"]


class DocumentIndexOutcome(BaseModel):
    """What happened to one file during a `sync()` call."""

    document_id: str | None
    file_path: str
    status: DocumentOutcomeStatus
    num_chunks: int = 0
    error_message: str | None = None


class IndexingSummary(BaseModel):
    """Aggregate result of one `sync()` call — what a "Build/Update Index" UI shows."""

    outcomes: list[DocumentIndexOutcome]
    total_files_scanned: int
    total_indexed: int
    total_skipped_unchanged: int
    total_skipped_duplicate: int
    total_failed: int
    total_chunks_in_index: int
    duration_seconds: float


class IndexingPipeline:
    """Orchestrates loading, chunking, embedding, and storage for the whole corpus."""

    def __init__(
        self,
        repo: MetadataRepository | None = None,
        embedding_model: EmbeddingModel | None = None,
        vector_store: FAISSVectorStore | None = None,
        bm25_index: BM25SparseIndex | None = None,
    ) -> None:
        self.repo = repo or MetadataRepository()
        self.embedding_model = embedding_model or get_default_embedding_model()

        if vector_store is not None:
            self.vector_store = vector_store
        else:
            try:
                self.vector_store = FAISSVectorStore.load()
            except VectorStoreError as e:
                logger.warning(
                    "No usable FAISS index on disk (%s); starting with an empty index. "
                    "It will self-heal from stored chunk text on the next sync().",
                    e,
                )
                self.vector_store = FAISSVectorStore(dimension=self.embedding_model.dimension)

        if bm25_index is not None:
            self.bm25_index = bm25_index
        else:
            try:
                self.bm25_index = BM25SparseIndex.load()
            except BM25IndexError as e:
                logger.warning(
                    "No usable BM25 index on disk (%s); starting empty. "
                    "It fully rebuilds on every sync() regardless.",
                    e,
                )
                self.bm25_index = BM25SparseIndex()

    # -- public operations --------------------------------------------------------

    def sync(self, directory: Path | None = None) -> IndexingSummary:
        """Index every new/changed file under `directory`; skip unchanged ones.

        Always safe to call repeatedly — see module docstring for why
        this single method covers first-time indexing, incremental
        updates, and recovery from a corrupted/missing vector index.
        """
        start = time.time()
        directory = directory or settings.documents_path_resolved

        files = sorted(
            p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )

        needs_vector_repopulation = self.vector_store.is_empty and self.repo.count_chunks() > 0
        if needs_vector_repopulation:
            logger.warning(
                "Vector index is empty but %d chunk(s) exist in metadata; "
                "will repopulate vectors from stored chunk text where content is unchanged.",
                self.repo.count_chunks(),
            )

        outcomes = [self._sync_one_file(path, needs_vector_repopulation, directory) for path in files]

        self._rebuild_bm25_index()
        self._save_indexes()

        summary = IndexingSummary(
            outcomes=outcomes,
            total_files_scanned=len(files),
            total_indexed=sum(1 for o in outcomes if o.status == "indexed"),
            total_skipped_unchanged=sum(1 for o in outcomes if o.status == "skipped_unchanged"),
            total_skipped_duplicate=sum(1 for o in outcomes if o.status == "skipped_duplicate"),
            total_failed=sum(1 for o in outcomes if o.status == "failed"),
            total_chunks_in_index=len(self.vector_store),
            duration_seconds=time.time() - start,
        )
        logger.info(
            "Sync complete: scanned=%d indexed=%d skipped_unchanged=%d "
            "skipped_duplicate=%d failed=%d chunks_in_index=%d duration=%.2fs",
            summary.total_files_scanned,
            summary.total_indexed,
            summary.total_skipped_unchanged,
            summary.total_skipped_duplicate,
            summary.total_failed,
            summary.total_chunks_in_index,
            summary.duration_seconds,
        )
        return summary

    def rebuild(self, directory: Path | None = None) -> IndexingSummary:
        """Wipe all indexes and metadata, then re-index everything from scratch."""
        logger.warning("Rebuilding index from scratch: all existing metadata/vectors will be wiped.")
        self.delete_all()
        return self.sync(directory)

    def delete_all(self) -> None:
        """Wipe SQLite documents/chunks, the FAISS index, and the BM25 index.

        Preserves `self.vector_store.path`/`self.bm25_index.path` on the
        replacement empty instances — without this, a fresh
        `FAISSVectorStore(...)`/`BM25SparseIndex()` with no `path` would
        make the next `_save_indexes()` call fall back to
        `settings.vector_path_resolved`/`settings.bm25_path_resolved`
        instead of wherever THIS pipeline's indexes actually live
        (relevant for any caller managing a non-default location, e.g.
        tests isolated to a temp directory).
        """
        self.repo.delete_all()
        self.vector_store = FAISSVectorStore(
            dimension=self.embedding_model.dimension, path=self.vector_store.path
        )
        self.bm25_index = BM25SparseIndex(path=self.bm25_index.path)
        self._save_indexes()
        logger.warning("Deleted all documents, chunks, and indexes.")

    def remove_document(self, document_id: str) -> None:
        """Remove one document: its metadata, chunks, and vectors; rebuild BM25."""
        chunks = self.repo.get_chunks_for_document(document_id)
        self.vector_store.remove([c.id for c in chunks])
        self.repo.delete_document(document_id)
        self._rebuild_bm25_index()
        self._save_indexes()
        logger.info("Removed document_id=%s (%d chunk(s))", document_id, len(chunks))

    # -- internals ------------------------------------------------------------------

    def _sync_one_file(self, path: Path, force_repopulate: bool, scan_root: Path) -> DocumentIndexOutcome:
        try:
            file_hash = compute_sha256(path)
        except OSError as e:
            logger.error("Could not read %s: %s", path, e)
            return DocumentIndexOutcome(
                document_id=None, file_path=str(path), status="failed", error_message=str(e)
            )

        existing_by_path = self.repo.get_document_by_path(str(path))

        if existing_by_path and existing_by_path.file_hash == file_hash:
            if not force_repopulate:
                return DocumentIndexOutcome(
                    document_id=existing_by_path.id,
                    file_path=str(path),
                    status="skipped_unchanged",
                    num_chunks=existing_by_path.num_chunks,
                )
            return self._repopulate_vectors_from_stored_chunks(existing_by_path)

        document_id = existing_by_path.id if existing_by_path else str(uuid.uuid4())

        existing_by_hash = self.repo.get_document_by_hash(file_hash)
        if existing_by_hash and existing_by_hash.id != document_id:
            logger.warning(
                "Skipping %s: identical content already indexed as '%s'",
                path,
                existing_by_hash.file_name,
            )
            return DocumentIndexOutcome(
                document_id=None,
                file_path=str(path),
                status="skipped_duplicate",
                error_message=f"Duplicate content of already-indexed '{existing_by_hash.file_name}'",
            )

        return self._process_file(
            path, document_id, file_hash, is_update=existing_by_path is not None, scan_root=scan_root
        )

    def _repopulate_vectors_from_stored_chunks(self, doc: DocumentRecord) -> DocumentIndexOutcome:
        """Re-embed and re-add vectors for a document whose text hasn't changed.

        Used only when the vector index itself was found empty/corrupted
        at startup — the chunk text is already durable in SQLite, so this
        skips the expensive re-parse/re-chunk step entirely.
        """
        chunks = self.repo.get_chunks_for_document(doc.id)
        if chunks:
            embeddings = self.embedding_model.embed_documents([c.text for c in chunks])
            self.vector_store.add([c.id for c in chunks], embeddings)
        return DocumentIndexOutcome(
            document_id=doc.id, file_path=doc.file_path, status="indexed", num_chunks=len(chunks)
        )

    def _process_file(
        self, path: Path, document_id: str, file_hash: str, is_update: bool, scan_root: Path
    ) -> DocumentIndexOutcome:
        try:
            loaded_doc = load_document(path)
            chunk_drafts = chunk_document(loaded_doc, file_name=path.name)
        except DocumentLoadError as e:
            logger.error("Failed to load/chunk %s: %s", path, e)
            self._record_failed_document(path, document_id, file_hash, str(e), scan_root)
            return DocumentIndexOutcome(
                document_id=document_id, file_path=str(path), status="failed", error_message=str(e)
            )
        except Exception as e:  # noqa: BLE001 - one bad file must not abort the whole batch
            logger.exception("Unexpected error processing %s", path)
            self._record_failed_document(path, document_id, file_hash, f"Unexpected error: {e}", scan_root)
            return DocumentIndexOutcome(
                document_id=document_id, file_path=str(path), status="failed", error_message=str(e)
            )

        if is_update:
            old_chunks = self.repo.get_chunks_for_document(document_id)
            self.vector_store.remove([c.id for c in old_chunks])

        collection_category, collection_id, collection_title = derive_collection(path, scan_root)

        chunk_records = [
            ChunkRecord(
                id=ChunkRecord.make_id(document_id, d.chunk_index),
                document_id=document_id,
                collection_id=collection_id,
                collection_category=collection_category,
                collection_title=collection_title,
                **d.model_dump(),
            )
            for d in chunk_drafts
        ]
        law_name = chunk_drafts[0].law_name if chunk_drafts else None

        self.repo.upsert_document(
            DocumentRecord(
                id=document_id,
                file_name=path.name,
                file_path=str(path),
                file_type=loaded_doc.file_type,
                law_name=law_name,
                collection_id=collection_id,
                collection_category=collection_category,
                collection_title=collection_title,
                file_hash=file_hash,
                file_size_bytes=path.stat().st_size,
                num_chunks=len(chunk_records),
                status="indexed",
            )
        )
        self.repo.replace_chunks(document_id, chunk_records)

        if chunk_records:
            embeddings = self.embedding_model.embed_documents([c.text for c in chunk_records])
            self.vector_store.add([c.id for c in chunk_records], embeddings)

        return DocumentIndexOutcome(
            document_id=document_id, file_path=str(path), status="indexed", num_chunks=len(chunk_records)
        )

    def _record_failed_document(
        self, path: Path, document_id: str, file_hash: str, error: str, scan_root: Path
    ) -> None:
        collection_category, collection_id, collection_title = derive_collection(path, scan_root)
        self.repo.upsert_document(
            DocumentRecord(
                id=document_id,
                file_name=path.name,
                file_path=str(path),
                file_type=path.suffix.lstrip(".").lower() or "unknown",
                collection_id=collection_id,
                collection_category=collection_category,
                collection_title=collection_title,
                file_hash=file_hash,
                file_size_bytes=path.stat().st_size if path.exists() else 0,
                status="failed",
                error_message=error,
            )
        )

    def _rebuild_bm25_index(self) -> None:
        all_chunks = self.repo.get_all_chunks()
        self.bm25_index.build([c.id for c in all_chunks], [c.text for c in all_chunks])

    def _save_indexes(self) -> None:
        self.vector_store.save()
        self.bm25_index.save()
