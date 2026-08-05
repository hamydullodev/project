"""Reusable animation helpers: skeleton loaders, typing dots, fade/scale."""

from __future__ import annotations

import streamlit as st


def typing_indicator() -> None:
    """Render an animated "..." typing indicator while the agent thinks."""
    st.markdown(
        '<div class="typing-dots"><span></span><span></span><span></span></div>',
        unsafe_allow_html=True,
    )


def skeleton_card(count: int = 3) -> None:
    """Render ``count`` pulsing skeleton placeholders for loading results."""
    for _ in range(count):
        st.markdown(
            '<div class="glass-card fade-in" style="height:64px;opacity:0.4;"></div>',
            unsafe_allow_html=True,
        )
