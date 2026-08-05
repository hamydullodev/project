"""Chat panel: blue user bubbles, borderless assistant text, streaming reveal.

The LangGraph checkpointer (:mod:`app.agent.graph`) is the single source of
truth for chat history — this module only renders it and feeds new turns
in, rather than keeping a second copy of the conversation in
``st.session_state``.
"""

from __future__ import annotations

import html
import time
import uuid

import markdown as md
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.graph import get_graph
from app.api.exceptions import ProviderError
from app.ui.components.notification import render_notice
from app.utils.logger import get_logger
from app.utils.speech import transcribe_audio

logger = get_logger(__name__)

_PLACEHOLDER = "Masalan: Toshkentdan Istanbulga eng arzon reys top"


def _thread_config() -> dict:
    thread_id = st.session_state.setdefault("thread_id", str(uuid.uuid4()))
    return {"configurable": {"thread_id": thread_id}}


def _current_messages() -> list:
    graph = get_graph()
    state = graph.get_state(_thread_config())
    return state.values.get("messages", []) if state.values else []


def has_messages() -> bool:
    """Whether the current thread has any chat history yet."""
    return bool(_current_messages())


def _to_html(role: str, content: str) -> str:
    if role == "user":
        return f"<p>{html.escape(content)}</p>"
    # Convert to HTML server-side (rather than relying on Streamlit's client
    # markdown renderer) so tables/lists inside our custom div don't get
    # mis-parsed and leak raw closing tags as visible text.
    return md.markdown(content, extensions=["tables", "nl2br", "fenced_code"])


def _render_bubble(role: str, content: str) -> None:
    st.markdown(
        f"""
        <div class="bubble-row {role}">
            <div class="bubble {role}">{_to_html(role, content)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _reveal_assistant_reply(text: str) -> None:
    """Animate the (already fully computed) reply appearing word by word.

    This is a UI reveal animation, not live token generation — the full
    turn (including any tool calls) already ran in :func:`_run_turn`. A
    table in the answer is shown immediately instead of animated, since a
    partially-revealed markdown table renders as garbled text mid-animation.
    """
    placeholder = st.empty()
    if "|" in text:
        with placeholder.container():
            _render_bubble("assistant", text)
        return

    words = text.split(" ")
    shown: list[str] = []
    step = max(1, len(words) // 60)
    for i in range(0, len(words), step):
        shown.extend(words[i : i + step])
        with placeholder.container():
            _render_bubble("assistant", " ".join(shown))
        time.sleep(0.02)
    with placeholder.container():
        _render_bubble("assistant", text)


def _run_turn(text: str) -> str | None:
    """Run one agent turn for ``text`` and return the assistant's reply."""
    graph = get_graph()
    config = _thread_config()
    try:
        result = graph.invoke({"messages": [HumanMessage(content=text)]}, config=config)
    except ProviderError as exc:
        logger.error("Agent turn failed: {}", exc)
        st.session_state["last_error"] = str(exc)
        return None

    for message in reversed(result.get("messages", [])):
        if isinstance(message, AIMessage) and message.content:
            return str(message.content)
    return None


def render_chat() -> None:
    """Render the full chat history and the input box for new turns."""
    for message in _current_messages():
        if isinstance(message, HumanMessage):
            _render_bubble("user", str(message.content))
        elif isinstance(message, AIMessage) and message.content:
            _render_bubble("assistant", str(message.content))

    last_error = st.session_state.pop("last_error", None)
    if last_error:
        render_notice(last_error, title="Nimadir xato ketdi")

    submission = st.chat_input(
        _PLACEHOLDER,
        accept_file=True,
        accept_audio=True,
        file_type=["pdf", "png", "jpg", "jpeg"],
    )
    if not submission:
        return

    text = submission.text if hasattr(submission, "text") else str(submission)
    files = getattr(submission, "files", None) or []
    audio = getattr(submission, "audio", None)

    if files:
        names = ", ".join(f.name for f in files)
        render_notice(
            f"📎 {names} qabul qilindi, lekin fayl mazmunini tahlil qilish "
            "hozircha ulanmagan — iltimos savolingizni matn bilan yozing.",
            title="Fayl qabul qilindi",
            kind="info",
        )
    if audio is not None:
        with st.spinner("Ovozli xabar matnga aylantirilmoqda..."):
            try:
                transcribed = transcribe_audio(audio)
            except Exception:
                logger.exception("Speech-to-text failed")
                render_notice(
                    "Ovozli xabarni matnga aylantirib bo'lmadi. Iltimos matn bilan yozing.",
                    title="Nimadir xato ketdi",
                )
                transcribed = ""
        if transcribed:
            text = transcribed
            render_notice(f'🎤 Aniqlangan matn: "{transcribed}"', title="Ovozli xabar", kind="info")
        elif not text:
            render_notice(
                "Ovozli xabarda matn aniqlanmadi. Iltimos qayta urinib ko'ring yoki matn bilan yozing.",
                title="Diqqat",
                kind="info",
            )

    if not text:
        return

    _render_bubble("user", text)
    with st.spinner("Avia AI o'ylayapti..."):
        reply = _run_turn(text)

    if reply:
        _reveal_assistant_reply(reply)
    st.rerun()
