"""Unit tests for app.config.collections.derive_collection()."""

from __future__ import annotations

from pathlib import Path

from app.config.collections import KNOWN_TITLES, derive_collection


def test_derive_collection_from_known_category_and_slug():
    root = Path("/data/txt")
    path = root / "kodekslar" / "jinoyat_kodeksi" / "document.txt"

    category, collection_id, title = derive_collection(path, root)

    assert category == "kodekslar"
    assert collection_id == "jinoyat_kodeksi"
    assert title == KNOWN_TITLES["jinoyat_kodeksi"]


def test_derive_collection_falls_back_to_prettified_title_for_unknown_slug():
    root = Path("/data/txt")
    path = root / "qonunlar" / "yangi_qonun_slugi" / "document.txt"

    category, collection_id, title = derive_collection(path, root)

    assert category == "qonunlar"
    assert collection_id == "yangi_qonun_slugi"
    assert title == "Yangi Qonun Slugi"


def test_derive_collection_handles_flat_file_with_no_category_folder():
    root = Path("/data/documents")
    path = root / "some_law" / "file.txt"

    category, collection_id, _title = derive_collection(path, root)

    assert category == "other"
    assert collection_id == "some_law"


def test_derive_collection_new_folder_needs_no_registry_entry():
    """The whole point of folder-driven collections: dropping a brand-new
    slug in still works with zero code/registry changes."""
    root = Path("/data/txt")
    path = root / "kodekslar" / "completely_new_kodeks" / "document.txt"

    category, collection_id, title = derive_collection(path, root)

    assert category == "kodekslar"
    assert collection_id == "completely_new_kodeks"
    assert title  # non-empty fallback, no KeyError
