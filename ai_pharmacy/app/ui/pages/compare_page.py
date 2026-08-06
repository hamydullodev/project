"""Compare Prices page: side-by-side comparison of the user's picked products."""

from __future__ import annotations

import streamlit as st

from app.ui.components.comparison import render_comparison
from app.ui.state import get_last_results
from app.ui.utils import product_id


def render() -> None:
    st.markdown("## ⚖️ Narxlarni solishtirish")

    compare_ids = st.session_state.get("compare_ids", set())
    products = [p for p in get_last_results() if product_id(p) in compare_ids]
    render_comparison(products)
