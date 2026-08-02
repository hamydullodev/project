"""
Chat page: the actual question-answering interface.

WHY THIS PAGE EXISTS
-----------------------
Every prior milestone (2, 5-14) built toward exactly this: a user types a
legal question in Uzbek and gets a grounded, cited answer streamed back
in real time, with the sources it was built from. This page is
`RAGPipeline` (Milestone 14) wired to Streamlit's native chat widgets.

WHY st.session_state HOLDS FULL RerankedResult OBJECTS, NOT JUST TEXT
--------------------------------------------------------------------------
`st.session_state.chat_history` stores each assistant turn's complete
`list[RerankedResult]` (Milestone 9's model, carrying every score —
dense, sparse, combined, reranker — plus law name/article/section/page),
not just the rendered source-card text. Streamlit reruns the WHOLE page
script on every interaction, including re-rendering every message already
in history — storing the full objects means old messages' source cards
re-render with full detail (expandable chunks, per-score breakdown) every
time, exactly as detailed as when they were first generated, at no extra
computation cost (no re-querying, just re-rendering already-known data).

WHY THE COPY AFFORDANCE USES st.code() INSTEAD OF A CUSTOM JS BUTTON
--------------------------------------------------------------------------
Streamlit's `st.code(text, language=None)` renders a copyable block with
a built-in copy icon (shown on hover) — a genuinely native widget, so it
automatically matches whichever theme (light/dark) the user has chosen,
same reasoning as `components.py`'s docstring on avoiding hand-rolled
HTML/CSS. A custom `<button onclick="navigator.clipboard...">` would need
its own hardcoded colors to look intentional, and would need those colors
maintained in both light AND dark variants to not look broken in one of
them — extra maintenance for a strictly worse result than a widget
Streamlit already provides. It's tucked inside a collapsed expander so it
doesn't visually clutter every answer with a monospace block by default.

WHY "Suhbatni tozalash" (CLEAR CHAT) EXISTS EVEN THOUGH THE SPEC DOESN'T
LIST IT EXPLICITLY
--------------------------------------------------------------------------
`st.session_state.chat_history` persists for the lifetime of the browser
session — without an explicit way to reset it, a user testing different
questions has no way back to a clean slate short of reloading the whole
page (which Streamlit's own multi-page navigation doesn't require, so it
isn't even an obvious workaround). A one-line reset button is cheap
insurance for very little added surface area.
"""

from __future__ import annotations

from collections.abc import Iterator

import streamlit as st

from app.llm import LLMConnectionError, LLMModelNotFoundError
from app.rag import EmptyQueryError
from app.reranker import RerankedResult
from app.ui.components import render_chunk_card, render_page_header
from app.ui.resources import get_pipeline

CHAT_HISTORY_KEY = "chat_history"


def render() -> None:
    render_page_header("Qonunlar asosida savol-javob.")
    st.caption(
        "💡 Qorongʻu rejim uchun yuqori oʻng burchakdagi menyu (⋮) → Settings → Theme dan foydalaning."
    )

    if CHAT_HISTORY_KEY not in st.session_state:
        st.session_state[CHAT_HISTORY_KEY] = []

    try:
        pipeline = get_pipeline()
    except (LLMConnectionError, LLMModelNotFoundError) as e:
        st.error(f"❌ Til modeliga ulanib boʻlmadi: {e}")
        st.info("Ollama ishga tushirilganligiga ishonch hosil qiling: `ollama serve`")
        return

    _render_history()

    user_input = st.chat_input("Savolingizni yozing...")
    if user_input:
        _handle_new_question(pipeline, user_input)

    # Placed in the sidebar, but only AFTER handling this run's new
    # question (if any) — st.sidebar content renders in the sidebar
    # region regardless of where in the script it's called, so this can
    # safely sit at the bottom to read session_state POST-update. An
    # earlier version put this near the top of render() and gated it
    # `if history:` — that read session_state BEFORE the new question was
    # appended in this same script pass, so the button was always one
    # interaction "behind" (it wouldn't reflect a just-asked first
    # question until the NEXT rerun). Reading state after the update it
    # depends on, not before, is the actual fix — moving the button's
    # visual location alone (a first, incomplete attempt) does not
    # change *when* in the script its condition is evaluated.
    with st.sidebar:
        if st.button("🗑️ Suhbatni tozalash", disabled=not st.session_state[CHAT_HISTORY_KEY]):
            st.session_state[CHAT_HISTORY_KEY] = []
            st.rerun()


def _render_history() -> None:
    for i, message in enumerate(st.session_state[CHAT_HISTORY_KEY]):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                _render_sources(message["sources"])
            if message["role"] == "assistant":
                _render_answer_actions(message["content"], key_prefix=f"history_{i}")


def _handle_new_question(pipeline, user_input: str) -> None:
    st.session_state[CHAT_HISTORY_KEY].append({"role": "user", "content": user_input, "sources": None})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        try:
            context, stream = pipeline.ask_stream(user_input)
        except EmptyQueryError:
            st.warning("Iltimos, savol kiriting.")
            st.session_state[CHAT_HISTORY_KEY].pop()  # remove the empty user turn
            return

        # st.write_stream()'s return type is `str | list[Any]` since it also
        # accepts generators yielding non-string chunks; `_as_text_generator`
        # always yields plain str, so the result is always a str here.
        answer_text = str(st.write_stream(_as_text_generator(stream)))
        sources = context.compression.kept

        if sources:
            _render_sources(sources)
        new_index = len(st.session_state[CHAT_HISTORY_KEY])
        _render_answer_actions(answer_text, key_prefix=f"new_{new_index}")

    st.session_state[CHAT_HISTORY_KEY].append(
        {"role": "assistant", "content": answer_text, "sources": sources}
    )


def _as_text_generator(stream: Iterator[str]) -> Iterator[str]:
    """Adapts OllamaLLM.stream()'s Iterator[str] for st.write_stream().

    A thin pass-through — `st.write_stream` already accepts a plain
    generator of strings directly. This wrapper exists so the type is
    unambiguous at the call site and to keep a single place to adapt the
    stream shape if that's ever needed (e.g. inserting a delay, or
    filtering empty chunks) without touching `_handle_new_question`.
    """
    yield from stream


def _render_sources(sources: list[RerankedResult]) -> None:
    st.markdown(f"**📚 Manbalar** ({len(sources)} ta)")
    for i, source in enumerate(sources, start=1):
        render_chunk_card(i, source)


def _render_answer_actions(answer_text: str, key_prefix: str) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ Yuklab olish",
            data=answer_text,
            file_name="javob.txt",
            mime="text/plain",
            key=f"download_{key_prefix}",
        )
    with col2, st.expander("📋 Nusxalash uchun"):
        st.code(answer_text, language=None)


# See app/ui/pages/chat.py's original placeholder comment (now replaced
# by this real page) for why this guard exists: lets this file run
# standalone (streamlit run / AppTest.from_file) without double-rendering
# when app.ui.navigation imports it normally.
if __name__ == "__main__":
    render()
