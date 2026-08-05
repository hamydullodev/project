"""
Unit tests for app.ui.pages.retrieval_debug (Milestone 18).

Runs against the REAL `RAGPipeline` over this project's actual indexed
corpus, for the same reason `test_chat_page.py` does (see that file's
docstring): `RAGPipeline` has no single settings knob to redirect into an
isolated fake instance the way `get_repo()`'s `MetadataRepository` does,
and the real corpus is now genuinely present as part of this project's
own state (populated during Milestone 16's verification) — testing
against it is representative, not test pollution.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

PAGE_PATH = str(Path(__file__).resolve().parent.parent / "app" / "ui" / "pages" / "retrieval_debug.py")

REAL_QUESTION = "Ish beruvchi mehnat shartnomasini qanday bekor qiladi?"


def test_retrieval_debug_page_renders_without_errors():
    at = AppTest.from_file(PAGE_PATH, default_timeout=60)
    at.run()

    assert not at.exception


def test_retrieval_debug_page_shows_text_input_and_search_button():
    at = AppTest.from_file(PAGE_PATH, default_timeout=60)
    at.run()

    assert len(at.text_input) == 1
    search_buttons = [b for b in at.button if "qidirish" in b.label.lower()]
    assert len(search_buttons) == 0  # button only appears once a query is entered


def test_searching_shows_score_table_and_chunk_cards():
    at = AppTest.from_file(PAGE_PATH, default_timeout=90)
    at.run()

    at.text_input[0].set_value(REAL_QUESTION).run()
    search_buttons = [b for b in at.button if "qidirish" in b.label.lower()]
    assert len(search_buttons) == 1

    search_buttons[0].click().run(timeout=90)

    assert not at.exception
    assert len(at.dataframe) >= 1

    metric_values = [m.value for m in at.metric]
    assert any(v != "0" for v in metric_values)  # real hits found


def test_searched_results_include_status_labels():
    at = AppTest.from_file(PAGE_PATH, default_timeout=90)
    at.run()
    at.text_input[0].set_value(REAL_QUESTION).run()
    [b for b in at.button if "qidirish" in b.label.lower()][0].click().run(timeout=90)

    df = at.dataframe[0].value
    assert "Holat" in df.columns
    assert "Dense" in df.columns
    assert "Sparse" in df.columns
    assert "Rerank" in df.columns
    # At least one kept result should be labeled as such.
    assert df["Holat"].str.contains("Saqlangan").any()
