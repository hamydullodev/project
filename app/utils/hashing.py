"""
Content hashing — the mechanism behind document deduplication.

WHY THIS MODULE EXISTS
-----------------------
`MetadataRepository.get_document_by_hash()` (Milestone 2) and the
indexing pipeline (Milestone 10) both need a stable fingerprint of a
file's *content* to answer two questions: "have I already indexed this
exact file?" (skip re-ingestion) and "has this file changed since I last
indexed it?" (re-chunk only what changed). A cryptographic hash of the raw
bytes answers both: identical bytes always hash identically, and changing
even one byte changes the hash completely (the avalanche effect), so
there's no need to compare file contents directly or trust file
modification timestamps (which are unreliable — copying a file often
resets its mtime).

HOW IT WORKS INTERNALLY
------------------------
SHA-256 is computed by streaming the file in fixed-size chunks rather than
`path.read_bytes()` in one call. For the ~1MB legal-code text files in
this project the difference is irrelevant, but streaming means the
function's memory usage stays flat (O(1), not O(file size)) even if a
user later uploads a large multi-hundred-page PDF.

TIME / MEMORY COMPLEXITY
-------------------------
O(n) time in file size (every byte must be read and hashed once), O(1)
memory (fixed 64KB buffer regardless of file size).

ALTERNATIVES CONSIDERED
-------------------------
- MD5: faster, but this isn't a security context where collision
  resistance matters much — SHA-256 is used anyway because it's the
  Python standard library default people reach for and collisions in
  practice are a non-issue at this corpus size.
- File mtime/size as a proxy for "changed": rejected — unreliable (a
  `git clone` or `cp -p` can preserve or reset mtimes inconsistently) and
  doesn't detect a same-size edit.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE_BYTES = 64 * 1024


def compute_sha256(path: Path) -> str:
    """Return the hex-encoded SHA-256 digest of a file's raw bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(_CHUNK_SIZE_BYTES):
            digest.update(chunk)
    return digest.hexdigest()
