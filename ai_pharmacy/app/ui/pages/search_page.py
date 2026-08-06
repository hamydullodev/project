"""Medicine Search: sort/filter controls over the most recent search."""

from __future__ import annotations

import streamlit as st

from app.ui.components.cards import render_product_cards
from app.ui.state import get_last_query, get_last_results
from app.ui.utils import compute_badges, market_summary

_SORT_OPTIONS = {
    "Narx (arzondan)": lambda p: (p.get("price") is None, p.get("price") or 0.0),
    "Nomi (A-Z)": lambda p: (p.get("name") or "").lower(),
    "Do'kon": lambda p: (p.get("store") or "").lower(),
}


def render() -> None:
    st.markdown("## 💊 Dori qidirish")

    results = get_last_results()
    if not results:
        render_product_cards([])
        return

    query = get_last_query()
    summary = market_summary(query, results)
    if summary:
        st.markdown(summary)

    brands = sorted({p["brand"] for p in results if p.get("brand")})
    stores = sorted({p["store"] for p in results if p.get("store")})

    col1, col2, col3, col4 = st.columns([2, 2, 2, 1.4])
    with col1:
        sort_label = st.selectbox("Saralash", list(_SORT_OPTIONS.keys()))
    with col2:
        chosen_brands = st.multiselect("Brend", brands, default=brands)
    with col3:
        chosen_stores = st.multiselect("Do'kon", stores, default=stores)
    with col4:
        only_available = st.checkbox("Faqat mavjud")

    filtered = [p for p in results if (not p.get("brand") or p["brand"] in chosen_brands)]
    filtered = [p for p in filtered if (not p.get("store") or p["store"] in chosen_stores)]
    if only_available:
        filtered = [p for p in filtered if p.get("in_stock", True)]
    filtered.sort(key=_SORT_OPTIONS[sort_label])

    st.caption(f"{len(filtered)} / {len(results)} mahsulot ko'rsatilmoqda")
    render_product_cards(filtered, key_prefix="search_", badges=compute_badges(filtered))
