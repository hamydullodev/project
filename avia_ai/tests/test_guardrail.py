"""Regression test for the anti-fabrication guard in app.agent.nodes.

This guards the PDF spec's hardest rule: the LLM must never invent flight
facts. A weak local model occasionally narrates a plausible price even when
the tool explicitly said "narx mavjud emas" — this test locks in that the
guard overrides that fabrication with the real tool output.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.nodes import _append_sources, _sanitize_final_answer


def _tool_message_without_price() -> ToolMessage:
    return ToolMessage(
        content="TAS -> IST uchun reyslar:\n| Reys | Narx |\n|---|---|\n| TK371 | narx mavjud emas |",
        tool_call_id="call-1",
        name="search_flights",
    )


def test_guard_overrides_fabricated_price():
    messages = [HumanMessage(content="reys top"), _tool_message_without_price()]
    fabricated = AIMessage(content="Eng arzoni TK371 — narxi 15,000.00 UZS")

    result = _sanitize_final_answer(fabricated, messages)

    assert "narx mavjud emas" in result.content.lower()
    assert "15,000" not in result.content


def test_guard_leaves_honest_answer_untouched():
    messages = [HumanMessage(content="reys top"), _tool_message_without_price()]
    honest = AIMessage(content="TK371 reysi topildi, ammo narx mavjud emas.")

    result = _sanitize_final_answer(honest, messages)

    assert result.content == honest.content


def test_guard_ignores_tool_calls_in_progress():
    messages = [HumanMessage(content="reys top"), _tool_message_without_price()]
    still_calling = AIMessage(
        content="",
        tool_calls=[{"name": "search_flights", "args": {}, "id": "call-2", "type": "tool_call"}],
    )

    result = _sanitize_final_answer(still_calling, messages)

    assert result is still_calling


def _web_search_tool_message() -> ToolMessage:
    return ToolMessage(
        content="- **Visa info**: O'zbekiston fuqarolari uchun viza kerak emas (https://example.com/visa)",
        tool_call_id="call-3",
        name="web_search",
    )


def test_append_sources_adds_missing_link():
    messages = [HumanMessage(content="Turkiya vizasi kerakmi?"), _web_search_tool_message()]
    no_link = AIMessage(content="Turkiyaga viza kerak emas.")

    result = _append_sources(no_link, messages)

    assert "https://example.com/visa" in result.content
    assert "https://example.com/visa)" not in result.content


def test_append_sources_leaves_answer_with_link_untouched():
    messages = [HumanMessage(content="Turkiya vizasi kerakmi?"), _web_search_tool_message()]
    has_link = AIMessage(content="Manba: https://example.com/visa. Viza kerak emas.")

    result = _append_sources(has_link, messages)

    assert result.content == has_link.content


def test_append_sources_ignores_non_web_search_tools():
    messages = [HumanMessage(content="reys top"), _tool_message_without_price()]
    answer = AIMessage(content="Reys topildi.")

    result = _append_sources(answer, messages)

    assert result.content == answer.content
