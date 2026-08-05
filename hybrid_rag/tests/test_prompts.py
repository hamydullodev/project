"""Unit tests for app.prompts (templates + builder)."""

from __future__ import annotations

from app.prompts.builder import _format_source, build_messages, format_context
from app.prompts.templates import NOT_FOUND_MESSAGE_UZ, SYSTEM_PROMPT_UZ
from app.reranker.cross_encoder import RerankedResult


def _chunk(**kwargs) -> RerankedResult:
    defaults = dict(chunk_id="c1", text="Matn namunasi.")
    defaults.update(kwargs)
    return RerankedResult(**defaults)


# ---------------------------------------------------------------------------
# _format_source
# ---------------------------------------------------------------------------


def test_format_source_includes_all_present_fields():
    chunk = _chunk(
        law_name="Mehnat kodeksi",
        article_number="155",
        section="1-BOB",
        page_number=3,
        text="Mehnat shartnomasini bekor qilish.",
    )
    rendered = _format_source(1, chunk)

    assert "--- Manba 1 ---" in rendered
    assert "Qonun: Mehnat kodeksi" in rendered
    assert "Modda: 155-modda" in rendered
    assert "Boʻlim: 1-BOB" in rendered
    assert "Sahifa: 3" in rendered
    assert "Matn: Mehnat shartnomasini bekor qilish." in rendered


def test_format_source_omits_missing_article_number():
    chunk = _chunk(law_name="Generic Doc", article_number=None, text="Matn.")
    rendered = _format_source(1, chunk)
    assert "Modda:" not in rendered
    assert "None" not in rendered


def test_format_source_omits_missing_section():
    chunk = _chunk(section=None, text="Matn.")
    rendered = _format_source(1, chunk)
    assert "Boʻlim:" not in rendered
    assert "None" not in rendered


def test_format_source_omits_missing_page_number():
    chunk = _chunk(page_number=None, text="Matn.")
    rendered = _format_source(1, chunk)
    assert "Sahifa:" not in rendered
    assert "None" not in rendered


def test_format_source_omits_missing_law_name():
    chunk = _chunk(law_name=None, text="Matn.")
    rendered = _format_source(1, chunk)
    assert "Qonun:" not in rendered
    assert "None" not in rendered


def test_format_source_numbering_reflects_index():
    chunk = _chunk()
    assert "--- Manba 3 ---" in _format_source(3, chunk)


# ---------------------------------------------------------------------------
# format_context
# ---------------------------------------------------------------------------


def test_format_context_empty_list_gives_placeholder():
    result = format_context([])
    assert "topilmadi" in result.lower()


def test_format_context_numbers_sources_in_given_order():
    chunks = [
        _chunk(chunk_id="a", text="Birinchi manba matni.", law_name="Kodeks A"),
        _chunk(chunk_id="b", text="Ikkinchi manba matni.", law_name="Kodeks B"),
    ]
    result = format_context(chunks)
    assert "--- Manba 1 ---" in result
    assert "--- Manba 2 ---" in result
    assert result.index("Manba 1") < result.index("Manba 2")
    assert "Birinchi manba matni." in result
    assert "Ikkinchi manba matni." in result


# ---------------------------------------------------------------------------
# build_messages
# ---------------------------------------------------------------------------


def test_build_messages_returns_system_and_user():
    messages = build_messages("Test savol?", [_chunk()])
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_messages_system_contains_instructions():
    messages = build_messages("Test savol?", [_chunk()])
    assert messages[0]["content"] == SYSTEM_PROMPT_UZ
    assert NOT_FOUND_MESSAGE_UZ in messages[0]["content"]


def test_build_messages_user_contains_question_and_context():
    chunk = _chunk(law_name="Mehnat kodeksi", article_number="155", text="Shartnoma bekor qilinadi.")
    messages = build_messages("Shartnoma qanday bekor qilinadi?", [chunk])

    user_content = messages[1]["content"]
    assert "Shartnoma qanday bekor qilinadi?" in user_content
    assert "Mehnat kodeksi" in user_content
    assert "155-modda" in user_content
    assert "Shartnoma bekor qilinadi." in user_content


def test_build_messages_with_no_chunks_still_produces_valid_prompt():
    messages = build_messages("Savol?", [])
    assert len(messages) == 2
    assert "Savol?" in messages[1]["content"]
    assert "topilmadi" in messages[1]["content"].lower()


def test_not_found_message_is_uzbek_and_nonempty():
    assert len(NOT_FOUND_MESSAGE_UZ) > 0
    assert "ʼ" in NOT_FOUND_MESSAGE_UZ or "maʼlumot" in NOT_FOUND_MESSAGE_UZ
