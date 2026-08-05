"""
FAISS-backed dense vector index: the "D" in dense retrieval.

WHY THIS MODULE EXISTS
-----------------------
Milestone 5 turns text into vectors; this module stores those vectors so
that, given a query vector, we can quickly find the chunks whose vectors
are closest to it. FAISS (Facebook AI Similarity Search) is a library
purpose-built for exactly this: it can hold millions of vectors and answer
nearest-neighbor queries far faster than a naive Python loop computing
similarity against every vector one at a time.

This module wraps FAISS behind a small, stable interface
(`build`/`add`/`remove`/`search`/`save`/`load`) so the rest of the app
never touches the `faiss` library directly, and — critically — handles the
one thing FAISS itself does NOT do: remembering which chunk each vector
belongs to.

WHY A SEPARATE ID MAPPING IS NEEDED
----------------------------------------
A raw FAISS index only stores vectors and returns *integer* positions or
ids from a search — it has no concept of "chunk_id" or any other
metadata. Since our chunk ids are strings (`"{document_id}::{chunk_index}"`,
see `ChunkRecord.make_id`), not the int64 values FAISS's `IndexIDMap`
requires, this module maintains its own bidirectional
`chunk_id <-> int64` mapping and persists it as a small JSON sidecar file
next to the binary FAISS index. On `search()`, FAISS gives us back int64
ids, which we translate back to chunk_ids the rest of the app understands
(and which `MetadataRepository.get_chunks_by_ids()` can then hydrate into
full `ChunkRecord`s with text and citation metadata).

An auto-incrementing counter (not a hash of the chunk_id string) generates
these int64 ids, specifically to avoid — even at negligible probability —
a hash collision silently overwriting an unrelated chunk's vector. An
explicit, persisted mapping is unambiguous and easy to inspect/debug,
which matters more here than saving one small JSON file.

WHY IndexFlatIP (EXACT SEARCH) INSTEAD OF AN APPROXIMATE INDEX
--------------------------------------------------------------------
FAISS offers both exact search (`IndexFlat*`, brute-force comparison
against every stored vector) and approximate nearest-neighbor indexes
(`IndexIVFFlat`, `IndexHNSWFlat`, etc.) that trade a small amount of
recall for much faster search at large scale. This project uses
`IndexFlatIP` (exact, inner-product) because:

  - Our corpus is a few thousand chunks (five legal codes), not millions —
    brute-force search over a few thousand ~400-1024 dimensional vectors
    takes low single-digit milliseconds, well within interactive latency.
  - Exact search has no recall trade-off to reason about or tune, which
    matters for a legal QA system where "the most relevant article wasn't
    even considered" is a worse failure mode than a few extra
    milliseconds of latency.
  - It requires no training step (`IndexIVFFlat` needs a k-means training
    pass over sample vectors before it can accept data — an added
    pipeline step irrelevant at this scale).

Inner product (`IP`), not L2 distance, is used because
`EmbeddingModel.embed_documents`/`embed_query` (Milestone 5) always
L2-normalize their output — for unit-length vectors, inner product IS
cosine similarity, and higher is better (unlike L2 distance, where lower
is better), which keeps score semantics ("higher score = more relevant")
consistent with BM25 scores later in the hybrid fusion step (Milestone 8).

HOW REMOVAL WORKS (FOR INCREMENTAL RE-INDEXING, MILESTONE 10)
-------------------------------------------------------------------
When a source document is edited and re-chunked, its old chunks' vectors
must be removed before the new ones are added — otherwise stale vectors
would keep surfacing in search results. `IndexIDMap.remove_ids` supports
removing specific vectors by their custom int64 id (unlike plain
`IndexFlat`, which only supports removal by fragile, reindex-on-delete
internal position) — this is the main reason this module wraps the flat
index in `IndexIDMap` rather than using `IndexFlatIP` directly.

TIME / MEMORY COMPLEXITY
-------------------------
- `add`: O(k · d) to encode k new vectors into the index (no training
  step, so insertion is just an append into FAISS's internal storage).
- `search`: O(n · d) per query (n = vectors currently in the index, d =
  dimension) — every vector is compared, since this is exact search.
- `remove`: O(n) — FAISS's `IndexIDMap.remove_ids` scans for matching ids.
- Memory: O(n · d · 4 bytes) for the vectors themselves (float32), plus
  O(n) for the id mapping — for 5,000 chunks at 384 dimensions, roughly
  7.7MB of vectors, negligible.

ADVANTAGES
-----------
- Exact, deterministic search results — no tuning, no recall/speed
  trade-off to reason about at this corpus size.
- The id-mapping sidecar makes the on-disk representation fully
  inspectable (plain JSON), which matters for an educational project and
  for debugging a "why didn't chunk X show up" question.

DISADVANTAGES
--------------
- `IndexFlatIP` does not scale to very large corpora (millions of
  vectors) — search time grows linearly with corpus size. Not a concern
  for a handful of legal codes, but a real constraint to know about.
- The id-mapping dicts are held fully in memory; for an extremely large
  chunk count this would need a more compact representation (e.g. array-
  based rather than dict-based), though this is far beyond the scale this
  project targets.

ALTERNATIVES CONSIDERED
-------------------------
- `IndexIVFFlat` / `IndexHNSWFlat` (approximate search): the right choice
  once a corpus grows into the hundreds of thousands to millions of
  vectors; deferred as a documented future upgrade path rather than
  adding tuning complexity (nlist, nprobe, ef_search, ...) this project's
  actual corpus size doesn't need.
- A managed/cloud vector database (Pinecone, Weaviate Cloud, etc.):
  rejected outright per the "fully local, no cloud" requirement.
- Storing the id mapping inside SQLite instead of a JSON sidecar: also
  reasonable (and Milestone 10 does keep chunk text/metadata in SQLite as
  the source of truth); a sidecar file was chosen so the FAISS index
  directory is self-contained and portable (copy two files, get a working
  index) without a required SQLite round-trip just to interpret it.

BEST PRACTICES APPLIED
------------------------
- `save`/`load` are atomic-ish: `save` writes to temporary filenames and
  renames into place, so a crash mid-write can't leave a half-written
  index file that `load` would then fail to parse (the "corrupted index"
  failure mode the spec asks to handle gracefully).
- `load` validates the sidecar's recorded dimension against the loaded
  FAISS index's own dimension and raises a clear `VectorStoreError`
  instead of a confusing downstream shape-mismatch exception if they
  disagree (e.g. from a manually-edited or mismatched pair of files).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStoreError(Exception):
    """Raised on a corrupted, missing, or inconsistent FAISS index/sidecar."""


class FAISSVectorStore:
    """Dense vector index over chunk embeddings, with a persisted chunk_id mapping.

    Remembers the path it was constructed or loaded with (`self.path`) so
    that `save()` called with no argument writes back to the SAME
    location by default, rather than silently falling back to the
    global `settings.vector_path_resolved` default. This matters for any
    caller managing multiple, differently-located indexes (e.g. tests
    isolating themselves to a temp directory) — without it, an
    unqualified `save()` call from such code would write into the real
    project's `indexes/` directory instead of the caller's intended
    location, exactly the kind of silent cross-contamination bug this
    attribute exists to prevent.
    """

    def __init__(self, dimension: int, path: Path | None = None) -> None:
        import faiss

        self.dimension = dimension
        self.path = path
        self._index = faiss.IndexIDMap(faiss.IndexFlatIP(dimension))
        self._chunk_id_to_int: dict[str, int] = {}
        self._int_to_chunk_id: dict[int, str] = {}
        self._next_id = 0

    def __len__(self) -> int:
        return self._index.ntotal

    @property
    def is_empty(self) -> bool:
        return len(self) == 0

    # -- mutation ---------------------------------------------------------------

    def add(self, chunk_ids: list[str], embeddings: np.ndarray) -> None:
        """Add (or replace) vectors for the given chunk ids.

        If any `chunk_ids` are already present, their old vectors are
        removed first — this makes `add` idempotent and safe to call
        during incremental re-indexing without producing duplicate
        entries for a chunk whose text (and therefore embedding) changed.
        """
        if len(chunk_ids) != embeddings.shape[0]:
            raise ValueError(
                f"chunk_ids length ({len(chunk_ids)}) must match embeddings "
                f"row count ({embeddings.shape[0]})"
            )
        if embeddings.shape[0] == 0:
            return
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} does not match "
                f"index dimension {self.dimension}"
            )

        already_present = [cid for cid in chunk_ids if cid in self._chunk_id_to_int]
        if already_present:
            self.remove(already_present)

        int_ids = np.empty(len(chunk_ids), dtype=np.int64)
        for i, chunk_id in enumerate(chunk_ids):
            new_id = self._next_id
            self._next_id += 1
            self._chunk_id_to_int[chunk_id] = new_id
            self._int_to_chunk_id[new_id] = chunk_id
            int_ids[i] = new_id

        self._index.add_with_ids(embeddings.astype(np.float32), int_ids)
        logger.info("Added %d vector(s) to FAISS index (total=%d)", len(chunk_ids), len(self))

    def remove(self, chunk_ids: list[str]) -> None:
        """Remove vectors for the given chunk ids, if present. No-op for unknown ids."""
        int_ids = [self._chunk_id_to_int[cid] for cid in chunk_ids if cid in self._chunk_id_to_int]
        if not int_ids:
            return

        import faiss

        selector = faiss.IDSelectorBatch(np.array(int_ids, dtype=np.int64))
        n_removed = self._index.remove_ids(selector)

        for cid in chunk_ids:
            int_id = self._chunk_id_to_int.pop(cid, None)
            if int_id is not None:
                self._int_to_chunk_id.pop(int_id, None)

        logger.info("Removed %d vector(s) from FAISS index (total=%d)", n_removed, len(self))

    # -- search -----------------------------------------------------------------

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[str, float]]:
        """Return up to `top_k` (chunk_id, similarity_score) pairs, best first.

        `similarity_score` is a cosine similarity in [-1, 1] (inner
        product of L2-normalized vectors) — higher is more relevant.
        """
        if self.is_empty:
            return []

        query = query_vector.astype(np.float32).reshape(1, -1)
        k = min(top_k, len(self))
        scores, ids = self._index.search(query, k)

        results: list[tuple[str, float]] = []
        for score, int_id in zip(scores[0], ids[0]):
            if int_id == -1:  # FAISS pads with -1 when fewer than k results exist
                continue
            chunk_id = self._int_to_chunk_id.get(int(int_id))
            if chunk_id is not None:
                results.append((chunk_id, float(score)))
        return results

    # -- persistence --------------------------------------------------------------

    def save(self, path: Path | None = None) -> None:
        """Persist the FAISS index and id mapping to disk.

        Writes to temporary files in the same directory and renames them
        into place, so a process crash mid-write leaves the previous
        valid files untouched rather than a half-written, corrupted pair.
        """
        import faiss

        index_path, meta_path = self._resolve_paths(path)
        index_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            dir=index_path.parent, suffix=".faiss.tmp", delete=False
        ) as tmp_index_file:
            tmp_index_path = Path(tmp_index_file.name)
        faiss.write_index(self._index, str(tmp_index_path))

        meta = {
            "dimension": self.dimension,
            "next_id": self._next_id,
            "chunk_id_to_int": self._chunk_id_to_int,
        }
        with tempfile.NamedTemporaryFile(
            mode="w", dir=meta_path.parent, suffix=".json.tmp", delete=False, encoding="utf-8"
        ) as tmp_meta_file:
            json.dump(meta, tmp_meta_file, ensure_ascii=False)
            tmp_meta_path = Path(tmp_meta_file.name)

        tmp_index_path.replace(index_path)
        tmp_meta_path.replace(meta_path)
        self.path = path or self.path  # remember this location for future unqualified save()s
        logger.info("Saved FAISS index (%d vectors) to %s", len(self), index_path)

    @classmethod
    def load(cls, path: Path | None = None) -> FAISSVectorStore:
        """Load a previously-saved index + id mapping from disk.

        Raises `VectorStoreError` (not a raw faiss/JSON exception) if
        either file is missing, unparsable, or the two are inconsistent
        with each other — the spec's "gracefully handle corrupted
        indexes" requirement. Callers (the indexing pipeline, the UI's
        "Rebuild Index" action) can catch this one exception type and
        trigger a rebuild from SQLite's `get_all_chunks()` rather than
        crashing.
        """
        import faiss

        index_path, meta_path = cls._resolve_paths_static(path)

        if not index_path.exists() or not meta_path.exists():
            raise VectorStoreError(f"FAISS index files not found at {index_path} / {meta_path}")

        try:
            index = faiss.read_index(str(index_path))
        except Exception as e:
            raise VectorStoreError(f"Could not read FAISS index at {index_path}: {e}") from e

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            raise VectorStoreError(f"Could not read index metadata at {meta_path}: {e}") from e

        required_keys = {"dimension", "next_id", "chunk_id_to_int"}
        if not required_keys.issubset(meta):
            raise VectorStoreError(
                f"Index metadata at {meta_path} is missing required keys: " f"{required_keys - meta.keys()}"
            )

        if meta["dimension"] != index.d:
            raise VectorStoreError(
                f"Metadata dimension ({meta['dimension']}) does not match "
                f"FAISS index dimension ({index.d}) — index and sidecar are inconsistent."
            )

        store = cls.__new__(cls)
        store.dimension = meta["dimension"]
        store.path = path
        store._index = index  # type: ignore[assignment]  # faiss.read_index()'s stub returns the generic Index base type; this file was always written as an IndexIDMap by this same class
        store._next_id = meta["next_id"]
        store._chunk_id_to_int = {k: int(v) for k, v in meta["chunk_id_to_int"].items()}
        store._int_to_chunk_id = {v: k for k, v in store._chunk_id_to_int.items()}

        if index.ntotal != len(store._chunk_id_to_int):
            raise VectorStoreError(
                f"Index vector count ({index.ntotal}) does not match id-mapping "
                f"size ({len(store._chunk_id_to_int)}) — index and sidecar are inconsistent."
            )

        logger.info("Loaded FAISS index (%d vectors) from %s", index.ntotal, index_path)
        return store

    @staticmethod
    def _resolve_paths_static(path: Path | None) -> tuple[Path, Path]:
        base = path or settings.vector_path_resolved
        return Path(str(base) + ".faiss"), Path(str(base) + ".meta.json")

    def _resolve_paths(self, path: Path | None) -> tuple[Path, Path]:
        return self._resolve_paths_static(path or self.path)
