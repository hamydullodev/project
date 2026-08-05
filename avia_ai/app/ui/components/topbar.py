"""Top bar: just the Avia AI logo. Everything else lives in the sidebar
navigation or the Sozlamalar page — a crowded top bar was explicitly called
out as clutter to remove.
"""

from __future__ import annotations

import streamlit as st


def render_topbar() -> None:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:10px; padding: 0.25rem 0 0.75rem 0;">
            <span class="avia-logo">✈️</span>
            <span class="gradient-text" style="font-size:1.35rem;">Avia AI</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
