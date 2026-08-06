"""History: past searches, with one click to ask the same query again."""

from __future__ import annotations

import time

import streamlit as st

from app.database.db import get_recent_searches
from app.ui.components import chat


def render() -> None:
    st.markdown("## 🕒 Qidiruvlar tarixi")

    recent = get_recent_searches(30)
    if not recent:
        st.info("Hali qidiruv tarixi bo'sh.")
        return

    for row in recent:
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(row["created_at"]))
        st.markdown(
            f"""
            <div class="glass-card fade-in">
                <div style="font-weight:700;">🔎 {row["query"]}</div>
                <div style="margin-top:4px; color:var(--text-muted); font-size:0.9rem;">
                    {row["result_count"]} ta natija · {ts}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Qayta qidirish", key=f"hist_{row['query']}_{row['created_at']}"):
            chat.send_message(row["query"])
