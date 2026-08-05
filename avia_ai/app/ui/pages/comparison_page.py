"""Taqqoslash page: side-by-side comparison of the last search result."""

from __future__ import annotations

import streamlit as st

from app.agent.memory import get_last_flights
from app.ui.components.comparison import render_comparison


def render() -> None:
    st.markdown("## 📊 Taqqoslash")
    render_comparison(get_last_flights())
