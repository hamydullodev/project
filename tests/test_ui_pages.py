"""
Unit tests for the Streamlit UI shell (Milestone 15).

Uses `streamlit.testing.v1.AppTest.from_file()`, which execs an actual
page file as a standalone script (imports and all), rather than
`AppTest.from_function()`, which only extracts a function's source text
and re-execs it in an isolated namespace with none of its module-level
imports available (documented Streamlit behavior: "the script must be
executable on its own"). Each page file has an
`if __name__ == "__main__": render()` guard at the bottom specifically
so it works as a standalone script under `AppTest.from_file` (and, as a
bonus, under a direct `streamlit run app/ui/pages/home.py`) without
double-rendering when `app.ui.navigation` imports it normally to obtain
`render` as a plain callable — see any page file's comment on that guard,
or `app.ui.navigation`'s module docstring, for the full reasoning.

Manual, real-browser verification (via Playwright driving an actual
running `streamlit run` server) was also done for this milestone,
covering the full click-through navigation and the Ollama connectivity
button — see the milestone report, not this file, for that.

`app.ui.pages.home.render()` calls `app.ui.resources.get_repo()`, whose
default construction points at the REAL project's
`settings.sqlite_path_resolved` — every test here that exercises the
Home page redirects that path first, for the same reason
`tests/test_pipeline.py` never lets `IndexingPipeline` fall back to its
real-path defaults.

The redirection can't be a simple `monkeypatch.setattr("app.ui.pages.
home.get_repo", ...)`: `AppTest.from_file` execs the target page file in
its OWN fresh module namespace (not the already-imported
`sys.modules["app.ui.pages.home"]"` this test process holds), so
patching an attribute on that already-imported module object has no
effect on AppTest's separately-exec'd copy. `app.config.settings` and
`app.database.repository`, however, are NOT re-exec'd by AppTest (only
the target page script is) — they stay the same cached modules in
`sys.modules` throughout. So `isolated_repo` instead patches the
`Settings` singleton's `sqlite_path` field directly: both this test's
own `MetadataRepository(...)` calls and the page script's internal
`get_repo() -> MetadataRepository()` end up reading the same patched
setting and therefore opening the very same on-disk SQLite file — real,
shared filesystem state is what actually crosses the module-identity
boundary here, not a shared Python object reference.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.database import MetadataRepository

PAGES_DIR = Path(__file__).resolve().parent.parent / "app" / "ui" / "pages"


@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MetadataRepository:
    import streamlit as st

    from app.config import settings as app_settings

    db_path = tmp_path / "ui_test.db"
    monkeypatch.setattr(app_settings, "sqlite_path", str(db_path))

    # get_repo() is @st.cache_resource-decorated; that cache is a
    # process-global singleton that otherwise persists across separate
    # AppTest.from_file() runs within one pytest session — without
    # clearing it, whichever test happens to call get_repo() FIRST would
    # "win" and every later test would silently see that first test's
    # cached repo/tmp_path instead of its own, regardless of this
    # fixture's monkeypatch. Streamlit-cached resources need explicit
    # cache invalidation between tests for exactly this reason.
    st.cache_resource.clear()

    return MetadataRepository(db_path=db_path)


# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------


def test_home_page_renders_without_errors(isolated_repo):
    at = AppTest.from_file(str(PAGES_DIR / "home.py"))
    at.run()

    assert not at.exception


def test_home_page_shows_app_title(isolated_repo):
    at = AppTest.from_file(str(PAGES_DIR / "home.py"))
    at.run()

    titles = " ".join(t.value for t in at.title)
    assert "Oʻzbekiston Qonunchiligi" in titles


def test_home_page_shows_zero_stats_for_empty_repo(isolated_repo):
    at = AppTest.from_file(str(PAGES_DIR / "home.py"))
    at.run()

    metric_values = [m.value for m in at.metric]
    assert "0" in metric_values  # documents and chunks both 0 for an empty repo


def test_home_page_reflects_repo_stats(isolated_repo):
    from app.database import ChunkRecord, DocumentRecord

    isolated_repo.upsert_document(
        DocumentRecord(
            id="doc-1", file_name="test.txt", file_path="/fake/test.txt", file_type="txt",
            law_name="Test kodeksi", file_hash="h1", file_size_bytes=100,
        )
    )
    isolated_repo.replace_chunks(
        "doc-1",
        [ChunkRecord(id="doc-1::00000", document_id="doc-1", chunk_index=0, text="matn",
                     char_count=4, law_name="Test kodeksi")],
    )

    at = AppTest.from_file(str(PAGES_DIR / "home.py"))
    at.run()

    metric_values = [m.value for m in at.metric]
    assert "1" in metric_values  # 1 document, 1 chunk both present
    markdown_text = " ".join(m.value for m in at.markdown)
    assert "Test kodeksi" in markdown_text


def test_home_page_warns_when_no_documents_indexed(isolated_repo):
    at = AppTest.from_file(str(PAGES_DIR / "home.py"))
    at.run()

    warning_text = " ".join(w.value for w in at.warning)
    assert "indeklanmagan" in warning_text or "boshlang" in warning_text


def test_home_page_quick_links_present(isolated_repo):
    at = AppTest.from_file(str(PAGES_DIR / "home.py"))
    at.run()

    labels = {link.label for link in at.get("page_link")}
    assert {"Savol berish", "Hujjat yuklash", "Indeksni qurish"}.issubset(labels)


# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------


def test_settings_page_renders_without_errors():
    at = AppTest.from_file(str(PAGES_DIR / "settings.py"))
    at.run()

    assert not at.exception


def test_settings_page_shows_configured_model():
    from app.config import settings as app_settings

    at = AppTest.from_file(str(PAGES_DIR / "settings.py"))
    at.run()

    full_text = " ".join(m.value for m in at.markdown)
    assert app_settings.llm_model in full_text


def test_settings_page_connectivity_button_does_not_crash():
    at = AppTest.from_file(str(PAGES_DIR / "settings.py"))
    at.run()
    at.button[0].click().run()

    assert not at.exception


# ---------------------------------------------------------------------------
# Placeholder pages (Milestones 17-19)
# ---------------------------------------------------------------------------
# "chat" is deliberately excluded here: it was a placeholder when this
# file was written for Milestone 15, but Milestone 16 replaced it with
# the real Chat page — see tests/test_chat_page.py for its coverage now.


@pytest.mark.parametrize(
    "module_name",
    ["upload", "index_management", "retrieval_debug", "statistics"],
)
def test_placeholder_page_renders_without_errors(module_name: str):
    at = AppTest.from_file(str(PAGES_DIR / f"{module_name}.py"))
    at.run()

    assert not at.exception
    info_text = " ".join(i.value for i in at.info)
    assert "tayyor emas" in info_text


# ---------------------------------------------------------------------------
# Navigation registry (pure Python, no Streamlit runtime needed)
# ---------------------------------------------------------------------------


def test_navigation_registry_covers_every_page_module():
    from app.ui.navigation import PAGES_BY_SECTION

    all_pages = [p for section_pages in PAGES_BY_SECTION.values() for p in section_pages]
    # StreamlitPage.title/.default aren't safely readable outside a live
    # script run in this Streamlit version - assert on _title/_default
    # (the underlying attributes) instead of the public properties.
    titles = {p._title for p in all_pages}

    required = {
        "Bosh sahifa", "Suhbat", "Hujjat yuklash", "Indeksni boshqarish",
        "Qidiruv tahlili", "Statistika", "Sozlamalar",
    }
    assert required.issubset(titles)


def test_navigation_home_page_is_default():
    from app.ui.navigation import home_page

    assert home_page._default is True
