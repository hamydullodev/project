"""Home page: the app's landing screen — hero when empty, chat otherwise."""

from __future__ import annotations

from app.ui.components import chat
from app.ui.components.hero import render_hero


def render() -> None:
    if not chat.has_messages():
        example = render_hero()
        if example:
            chat.send_message(example)
            return
    chat.render_chat()
