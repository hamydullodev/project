"""
Unit tests for app.ui.pages.index_management (Milestone 18).

`get_indexing_pipeline()` is deliberately uncached (see resources.py's
docstring), so — unlike the Home page's `get_repo()` — it can be
redirected per-test simply by monkeypatching `settings.documents_path`
and `settings.sqlite_path` before each `AppTest.from_file()` run: every
fresh `IndexingPipeline()` constructed inside the exec'd page script
reads the CURRENT (patched) settings at construction time, no shared
Python object identity required. Also patches `settings.vector_path`/
`settings.bm25_path` so save()/load() never touch the real project's
`indexes/` directory — the same isolation discipline established in
`tests/test_pipeline.py` (Milestone 10).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PAGE_PATH = str(Path(__file__).resolve().parent.parent / "app" / "ui" / "pages" / "index_management.py")

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

    st.cache_resource.clear()  # get_repo/get_pipeline must not leak from other tests

    return docs_dir


def test_index_management_page_renders_without_errors(isolated_paths: Path):
    at = AppTest.from_file(PAGE_PATH, default_timeout=150)
    at.run()

    assert not at.exception


def test_index_management_shows_zero_stats_for_empty_corpus(isolated_paths: Path):
    at = AppTest.from_file(PAGE_PATH, default_timeout=150)
    at.run()

    metric_values = [m.value for m in at.metric]
    assert "0" in metric_values


def test_sync_button_indexes_new_documents(isolated_paths: Path):
    (isolated_paths / "law.txt").write_text(SAMPLE_LAW, encoding="utf-8")

    at = AppTest.from_file(PAGE_PATH, default_timeout=150)
    at.run()

    sync_buttons = [b for b in at.button if "qurish / yangilash" in b.label.lower()]
    assert len(sync_buttons) == 1
    sync_buttons[0].click().run(timeout=150)

    assert not at.exception
    success_text = " ".join(s.value for s in at.success)
    assert "Tayyor!" in success_text


def test_rebuild_requires_confirmation(isolated_paths: Path):
    (isolated_paths / "law.txt").write_text(SAMPLE_LAW, encoding="utf-8")

    at = AppTest.from_file(PAGE_PATH, default_timeout=150)
    at.run()
    # Index it first so there's something to rebuild.
    [b for b in at.button if "qurish / yangilash" in b.label.lower()][0].click().run(timeout=150)

    rebuild_buttons = [b for b in at.button if b.label == "♻️ Nolldan qayta qurish"]
    assert len(rebuild_buttons) == 1
    rebuild_buttons[0].click().run()

    # Clicking once must NOT have rebuilt yet - only shown a confirmation.
    warning_text = " ".join(w.value for w in at.warning)
    assert "ortga qaytarib" not in warning_text  # that's delete's wording
    assert any("Davom etasizmi" in w.value for w in at.warning)

    confirm_buttons = [b for b in at.button if "Ha, qayta qurish" in b.label]
    assert len(confirm_buttons) == 1


def test_rebuild_confirmation_can_be_cancelled(isolated_paths: Path):
    at = AppTest.from_file(PAGE_PATH, default_timeout=150)
    at.run()
    [b for b in at.button if b.label == "♻️ Nolldan qayta qurish"][0].click().run()

    cancel_buttons = [b for b in at.button if b.label == "❌ Bekor qilish"]
    assert len(cancel_buttons) >= 1
    cancel_buttons[0].click().run()

    # Back to the non-confirming state - the original rebuild button is showing again.
    assert any(b.label == "♻️ Nolldan qayta qurish" for b in at.button)
    assert not any("Ha, qayta qurish" in b.label for b in at.button)


def test_delete_requires_confirmation_and_wipes_index(isolated_paths: Path):
    (isolated_paths / "law.txt").write_text(SAMPLE_LAW, encoding="utf-8")

    at = AppTest.from_file(PAGE_PATH, default_timeout=150)
    at.run()
    [b for b in at.button if "qurish / yangilash" in b.label.lower()][0].click().run(timeout=150)

    delete_buttons = [b for b in at.button if b.label == "🗑️ Indeksni oʻchirish"]
    assert len(delete_buttons) == 1
    delete_buttons[0].click().run()

    assert any("ortga qaytarib boʻlmaydi" in e.value for e in at.error)

    confirm_buttons = [b for b in at.button if "Ha, oʻchirish" in b.label]
    assert len(confirm_buttons) == 1
    confirm_buttons[0].click().run(timeout=30)

    assert not at.exception
    success_text = " ".join(s.value for s in at.success)
    assert "toʻliq oʻchirildi" in success_text
