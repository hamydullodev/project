"""Chat panel: blue user bubbles, borderless assistant text, streaming
reveal, with medicine result cards rendered inline under each assistant
turn that returned products.

Session state (:mod:`app.ui.state`) is the source of truth for the visible
conversation here, since the UI talks to the agent over HTTP rather than
holding the LangGraph checkpointer in-process.
"""

from __future__ import annotations

import html
import time

import markdown as md
import streamlit as st

from app.ui.components.cards import render_product_cards
from app.ui.components.notification import render_notice
from app.ui.state import set_last_search
from app.ui.utils import call_agent, compute_badges, extract_products

_PLACEHOLDER = "AI Pharmacy'dan so'rang... (masalan: Omega-3 eng arzon variantini top)"


def has_messages() -> bool:
    return bool(st.session_state.get("messages"))


def _to_html(role: str, content: str) -> str:
    if role == "user":
        return f"<p>{html.escape(content)}</p>"
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

    A numbered product list is shown immediately instead of animated, since
    a partially-revealed list of prices reads as garbled/misleading mid-turn.
    """
    placeholder = st.empty()
    if "|" in text or "\n1." in text:
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


def send_message(text: str) -> None:
    """Render the user bubble, run the turn, reveal the reply, and stash any
    returned products as the session's last search result."""
    _render_bubble("user", text)
    st.session_state.messages.append({"role": "user", "content": text})

    with st.spinner("AI Pharmacy o'ylayapti..."):
        result = call_agent(st.session_state.thread_id, text)

    products = extract_products(result.get("tool_results", []))
    if products:
        set_last_search(text, products)

    reply = result.get("answer", "")
    if reply:
        _reveal_assistant_reply(reply)
        if products:
            render_product_cards(
                products,
                key_prefix=f"chat_{len(st.session_state.messages)}_",
                badges=compute_badges(products),
            )
    else:
        render_notice("Agentdan javob olinmadi. Backend ishga tushganini tekshiring.")

    st.session_state.messages.append({"role": "assistant", "content": reply, "products": products})
    st.rerun()


def render_chat() -> None:
    """Render the full chat history and the input box for new turns."""
    for i, message in enumerate(st.session_state.messages):
        _render_bubble(message["role"], message["content"])
        if message.get("products"):
            render_product_cards(
                message["products"],
                key_prefix=f"hist_{i}_",
                badges=compute_badges(message["products"]),
            )

    submission = st.chat_input(_PLACEHOLDER)
    if not submission:
        return
    send_message(submission)
