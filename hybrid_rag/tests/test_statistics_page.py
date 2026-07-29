"""
Unit tests for app.ui.pages.statistics (Milestone 19).

Uses the same `isolated_paths` monkeypatching pattern as
`test_index_management_page.py` (documents/sqlite/vector/bm25 paths all
redirected into `tmp_path`) so these tests never touch the real project's
`indexes/`/`data/` — and, unlike `test_chat_page.py`/`test_retrieval_debug_page.py`,
this page never calls `get_pipeline()` (no embedding model load, no Ollama
dependency — see statistics.py's module docstring for why), so every test
here runs fast even without a real corpus or a running Ollama server.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PAGE_PATH = str(Path(__file__).resolve().parent.parent / "app" / "ui" / "pages" / "statistics.py")

SAMPLE_LAW = """\
TEST RESPUBLIKASINING SINOV KODEKSI
1-BOB.
UMUMIY QOIDALAR
1-modda. Birinchi modda
Bu birinchi moddaning matni sinov uchun yozilgan.
"""


@pytest.fixture()
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from app.config import settings as app_settings

    docs_dir = tmp_path / "documents"
    docs_dir.mkdir()
    monkeypatch.setattr(app_settings, "documents_path", str(docs_dir))
    monkeypatch.setattr(app_settings, "sqlite_path", str(tmp_path / "test.db"))
    monkeypatch.setattr(app_settings, "vector_path", str(tmp_path / "vectors"))
    monkeypatch.setattr(app_settings, "bm25_path", str(tmp_path / "bm25.pkl"))

    import streamlit as st

    st.cache_resource.clear()

    return docs_dir


def test_statistics_page_renders_without_errors(isolated_paths: Path):
    at = AppTest.from_file(PAGE_PATH, default_timeout=60)
    at.run()

    assert not at.exception


def test_statistics_page_shows_zero_stats_for_empty_corpus(isolated_paths: Path):
    at = AppTest.from_file(PAGE_PATH, default_timeout=60)
    at.run()

    metric_values = [m.value for m in at.metric]
    assert "0" in metric_values


def test_statistics_page_shows_dash_for_dimension_when_index_not_built(isolated_paths: Path):
    at = AppTest.from_file(PAGE_PATH, default_timeout=60)
    at.run()

    metric_values = [m.value for m in at.metric]
    assert "—" in metric_values  # embedding dimension / FAISS vectors, no index on disk yet
    caption_text = " ".join(c.value for c in at.caption)
    assert "hali qurilmagan" in caption_text


def test_statistics_page_reflects_real_index_after_sync(isolated_paths: Path):
    (isolated_paths / "law.txt").write_text(SAMPLE_LAW, encoding="utf-8")

    from app.ingestion import IndexingPipeline

    IndexingPipeline().sync()

    at = AppTest.from_file(PAGE_PATH, default_timeout=120)
    at.run()

    assert not at.exception
    metric_values = [m.value for m in at.metric]
    assert "1" in metric_values  # 1 document indexed
    # Embedding dimension should now be a real number, not the placeholder dash.
    assert any(v.isdigit() for v in metric_values)


def test_statistics_page_shows_memory_metric(isolated_paths: Path):
    at = AppTest.from_file(PAGE_PATH, default_timeout=60)
    at.run()

    assert not at.exception
    memory_metrics = [m for m in at.metric if "RSS" in m.label or "xotira" in m.label.lower()]
    assert len(memory_metrics) == 1
    assert memory_metrics[0].value != "—"
