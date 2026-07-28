"""
Unit tests for app.ui.pages.chat (Milestone 16).

Uses `AppTest.from_file()` (see test_ui_pages.py's docstring for why —
`AppTest.from_function()` drops module-level imports). Unlike the Home
page's tests, `get_pipeline()`'s `RAGPipeline` isn't easily redirected to
an isolated, fake instance the way `get_repo()` was in test_ui_pages.py:
`RAGPipeline()` has no single settings knob analogous to
`sqlite_path` to redirect. Rather than build elaborate machinery to fake
it, these tests run against the REAL pipeline over this project's
actual indexed corpus (populated as part of this milestone's own manual
verification — see the milestone report) — legitimate, representative
behavior, not test pollution, since indexing the real corpus is exactly
what a real user does before using this page.

This means the first test that calls `get_pipeline()` pays real model-
loading cost (~20-30s, per Milestones 5 and 9's own measurements);
`st.cache_resource`'s cache (a process-global singleton, per
test_ui_pages.py's discovery) makes every subsequent call in the same
pytest session fast, AS LONG AS nothing else in the session clears it —
`test_ui_pages.py`'s `isolated_repo` fixture does call
`st.cache_resource.clear()`, which clears every cached resource
process-wide (not just `get_repo`), so this file's tests may or may not
benefit from that caching depending on test execution order. Either way,
correctness doesn't depend on it — only wall-clock speed does.

A full, real-browser, real-question-and-answer walkthrough (typing a
question, streaming an answer, expanding a source card with its scores)
was also done manually via Playwright for this milestone — see the
milestone report, not this file, for that.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

CHAT_PAGE_PATH = str(Path(__file__).resolve().parent.parent / "app" / "ui" / "pages" / "chat.py")

# A question expected to retrieve real content from the indexed corpus
# (mehnat.txt / Labor Code, verified present via Milestone 10/14's own
# testing against this exact corpus).
REAL_QUESTION = "Ish beruvchi mehnat shartnomasini qanday bekor qiladi?"


def test_chat_page_renders_without_errors():
    at = AppTest.from_file(CHAT_PAGE_PATH, default_timeout=120)
    at.run()

    assert not at.exception


def test_chat_page_shows_chat_input_when_pipeline_available():
    at = AppTest.from_file(CHAT_PAGE_PATH, default_timeout=120)
    at.run()

    assert len(at.chat_input) == 1


def test_chat_page_starts_with_empty_history():
    at = AppTest.from_file(CHAT_PAGE_PATH, default_timeout=120)
    at.run()

    # The clear-chat button is always present (in the sidebar) but
    # disabled while there's no history to clear — see chat.py's comment
    # on why it's unconditionally rendered rather than conditionally.
    clear_buttons = [b for b in at.button if "tozalash" in b.label.lower()]
    assert len(clear_buttons) == 1
    assert clear_buttons[0].disabled is True


def test_asking_a_real_question_produces_a_grounded_answer_with_sources():
    at = AppTest.from_file(CHAT_PAGE_PATH, default_timeout=120)
    at.run()

    at.chat_input[0].set_value(REAL_QUESTION).run(timeout=120)

    assert not at.exception
    assert len(at.session_state["chat_history"]) == 2  # user turn + assistant turn

    user_turn, assistant_turn = at.session_state["chat_history"]
    assert user_turn["role"] == "user"
    assert user_turn["content"] == REAL_QUESTION
    assert assistant_turn["role"] == "assistant"
    assert len(assistant_turn["content"].strip()) > 0
    assert assistant_turn["sources"], "expected at least one retrieved source"
    assert assistant_turn["sources"][0].law_name is not None


def test_asked_question_shows_download_button():
    at = AppTest.from_file(CHAT_PAGE_PATH, default_timeout=120)
    at.run()
    at.chat_input[0].set_value(REAL_QUESTION).run(timeout=120)

    assert not at.exception
    assert len(at.get("download_button")) >= 1


def test_clear_chat_button_enables_after_history_and_resets_it():
    at = AppTest.from_file(CHAT_PAGE_PATH, default_timeout=120)
    at.run()
    at.chat_input[0].set_value(REAL_QUESTION).run(timeout=120)

    clear_buttons = [b for b in at.button if "tozalash" in b.label.lower()]
    assert len(clear_buttons) == 1
    assert clear_buttons[0].disabled is False  # now enabled, history exists

    clear_buttons[0].click().run(timeout=30)
    assert at.session_state["chat_history"] == []
