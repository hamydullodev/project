"""Unit tests for app.utils.device (shared by the embedder and reranker)."""

from __future__ import annotations

from app.utils.device import resolve_device


def test_resolve_device_passes_through_explicit_choice():
    assert resolve_device("cpu") == "cpu"
    assert resolve_device("cuda") == "cuda"
    assert resolve_device("mps") == "mps"


def test_resolve_device_auto_returns_a_valid_device():
    resolved = resolve_device("auto")
    assert resolved in ("cuda", "mps", "cpu")
