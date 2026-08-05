"""Sidebar extras: just the "+ Yangi suhbat" button.

Page navigation itself (Chat / Flight Results / Taqqoslash / Viza xizmati /
Sozlamalar) is handled natively by ``st.navigation`` in main.py, which
already renders a clean, collapsible, active-page-highlighted list in the
sidebar — reimplementing that by hand would just be a worse copy of what
Streamlit gives for free.
"""

from __future__ import annotations

import uuid

import streamlit as st


def render_new_chat_button() -> None:
    if st.button("+ Yangi suhbat", use_container_width=True, type="primary"):
        st.session_state["messages"] = []
        st.session_state["thread_id"] = str(uuid.uuid4())
        st.rerun()
