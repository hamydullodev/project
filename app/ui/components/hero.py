"""Hero shown when the chat is empty: a big airplane icon, title, subtitle.

Deliberately nothing else — no destination chips, no quick-action grid.
The brief asked for an "extremely clean" homepage where the user simply
asks the AI, so every button that used to sit here was removed rather than
kept as visual filler.
"""

from __future__ import annotations

import streamlit as st


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-wrap fade-in">
            <div class="hero-icon">✈️</div>
            <div class="hero-title">Qayerga sayohat qilmoqchisiz?</div>
            <div class="hero-subtitle">
                Reyslar, vizalar va sayohatni AI yordamida rejalashtiring.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
