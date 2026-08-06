"""Saved Medicines: the user's favorited products (SQLite-backed)."""

from __future__ import annotations

import streamlit as st

from app.database.db import list_favorites, remove_favorite
from app.ui.utils import format_price


def render() -> None:
    st.markdown("## ❤️ Saqlangan dorilar")

    favorites = list_favorites()
    if not favorites:
        st.info("Hozircha sevimlilar yo'q. Qidiruv natijalaridagi mahsulotni saqlab qo'yishingiz mumkin.")
        return

    for f in favorites:
        st.markdown(
            f"""
            <div class="glass-card fade-in">
                <div style="display:flex; justify-content:space-between; align-items:baseline;">
                    <span style="font-size:1.05rem; font-weight:700;">💊 {f["name"]}</span>
                    <span class="gradient-text" style="font-size:1.05rem;">
                        {format_price(f["price"], f["currency"])}
                    </span>
                </div>
                <div style="margin-top:4px; color:var(--text-muted); font-size:0.9rem;">
                    🏪 {f["store"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            if f.get("url"):
                st.link_button("🔗 Do'konga o'tish", f["url"], use_container_width=True)
        with col2:
            if st.button("🗑️ O'chirish", key=f"unfav_{f['id']}", use_container_width=True):
                remove_favorite(f["id"])
                st.rerun()
