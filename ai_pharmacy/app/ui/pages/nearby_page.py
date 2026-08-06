"""Nearby Pharmacies: the connected online pharmacies AI Pharmacy searches.

There's no geolocation/store-locator backend in this project, so this page
doesn't pretend to show live distance or open/closed status — it honestly
lists the real, connected pharmacy sites and links straight to them,
similar to how the flight card in Avia AI opens a real Google Flights
search instead of a fake booking flow.
"""

from __future__ import annotations

import streamlit as st

PHARMACIES = [
    {
        "name": "OXYmed",
        "url": "https://oxymed.uz",
        "description": "Dori-darmon va vitaminlar bo'yicha keng assortimentli internet dorixona.",
    },
    {
        "name": "PharmaClick",
        "url": "https://pharmaclick.uz",
        "description": "O'zbekistondagi yetakchi internet dorixonalaridan biri.",
    },
    {
        "name": "Europharm",
        "url": "https://europharm.uz",
        "description": "Import va mahalliy dori-darmonlar, vitaminlar bo'yicha internet dorixona.",
    },
]


def render() -> None:
    st.markdown("## 📍 Yaqin atrofdagi dorixonalar")
    st.info(
        "Hozircha jonli masofa yoki filiallar joylashuvi ulanmagan — bu bo'lim "
        "AI Pharmacy qidirayotgan uchta internet dorixonasini ko'rsatadi. "
        "Har biri o'z rasmiy saytiga olib boradi."
    )

    for pharmacy in PHARMACIES:
        st.markdown(
            f"""
            <div class="glass-card fade-in">
                <div style="font-size:1.05rem; font-weight:700;">🏪 {pharmacy["name"]}</div>
                <div style="margin-top:4px; color:var(--text-muted); font-size:0.92rem;">
                    {pharmacy["description"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.link_button(f"🔗 {pharmacy['name']}.uz'ga o'tish", pharmacy["url"])
