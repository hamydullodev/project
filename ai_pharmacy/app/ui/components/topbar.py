"""Top bar: just the AI Pharmacy logo. Everything else lives in the sidebar
navigation or the Sozlamalar page — a crowded top bar is clutter to avoid.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

_LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo_cropped.png"


@st.cache_data(show_spinner=False)
def _logo_data_uri() -> str:
    data = _LOGO_PATH.read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def render_topbar() -> None:
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:10px; padding: 0.25rem 0 0.75rem 0;">
            <span class="pharm-logo"><img src="{_logo_data_uri()}" alt="AI Pharmacy logo" /></span>
            <span class="gradient-text" style="font-size:1.35rem;">AI Pharmacy</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
