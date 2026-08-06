"""Sidebar extras: just the "+ Yangi qidiruv" button.

Page navigation itself (Home / Medicine Search / Compare Prices / Nearby
Pharmacies / Saved Medicines / History / Settings) is handled natively by
``st.navigation`` in app.py, which already renders a clean, collapsible,
active-page-highlighted list in the sidebar.
"""

from __future__ import annotations

import streamlit as st

from app.ui.state import reset_conversation


def render_new_search_button() -> None:
    if st.button("+ Yangi qidiruv", use_container_width=True, type="primary"):
        reset_conversation()
        st.rerun()
