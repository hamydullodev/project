"""Chat page: the app's home screen."""

from __future__ import annotations

from app.ui.components.chat import has_messages, render_chat
from app.ui.components.hero import render_hero


def render() -> None:
    if not has_messages():
        render_hero()
    render_chat()
