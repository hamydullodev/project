"""Elegant notification/error cards, replacing raw st.error boxes."""

from __future__ import annotations

import html

import streamlit as st


def render_notice(message: str, *, title: str = "Nimadir xato ketdi", kind: str = "error") -> None:
    """Render a friendly notice card instead of a raw error message.

    Args:
        message: The human-readable detail (already localized, no stack traces).
        title: Short headline, e.g. "Nimadir xato ketdi" or "Diqqat".
        kind: "error" or "info" — controls the accent color.
    """
    css_class = "notice-card" if kind == "error" else "notice-card info"
    icon = "⚠️" if kind == "error" else "ℹ️"
    st.markdown(
        f"""
        <div class="{css_class} fade-in">
            <div>{icon}</div>
            <div>
                <div class="notice-title">{html.escape(title)}</div>
                <div class="notice-body">{html.escape(message)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
