"""Unit tests for app.utils.hashing."""

from __future__ import annotations

from pathlib import Path

from app.utils.hashing import compute_sha256


def test_identical_content_same_hash(tmp_path: Path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("1-modda. Qonun matni.", encoding="utf-8")
    b.write_text("1-modda. Qonun matni.", encoding="utf-8")

    assert compute_sha256(a) == compute_sha256(b)


def test_different_content_different_hash(tmp_path: Path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("1-modda. Birinchi.", encoding="utf-8")
    b.write_text("1-modda. Ikkinchi.", encoding="utf-8")

    assert compute_sha256(a) != compute_sha256(b)


def test_hash_is_deterministic_across_calls(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_text("Barqaror matn", encoding="utf-8")

    assert compute_sha256(path) == compute_sha256(path)
