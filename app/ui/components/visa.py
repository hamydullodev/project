"""Visa info cards: each category is a real, cached Serper search result —
nothing here is a static template. Requirements/documents/cost/etc. for a
specific country change over time, so guessing would be actively harmful.
"""

from __future__ import annotations

import streamlit as st

from app.api.exceptions import ProviderError
from app.api.serper import get_serper_client
from app.utils.cache import cached

_CATEGORIES = [
    ("🛂", "Viza talablari va zarur hujjatlar", "{nat} fuqarolari uchun {dst} vizasi talablari va zarur hujjatlar"),
    ("🏛️", "Elchixona ma'lumotlari", "{dst} elchixonasi {nat} uchun manzil va aloqa"),
    ("⏱️", "Rasmiylashtirish muddati va narxi", "{dst} vizasi rasmiylashtirish muddati va narxi {nat} uchun"),
    ("📘", "Pasport va fotosurat talablari", "{dst} vizasi uchun pasport amal qilish muddati va fotosurat talablari"),
    ("📝", "Ariza topshirish bosqichlari", "{dst} vizasiga ariza topshirish bosqichlari"),
    ("⚠️", "Sayohat tavsiyalari", "{dst} sayohat xavfsizligi tavsiyalari {nat} fuqarolari uchun"),
]


@cached("visa_search")
def _search(query: str):
    return get_serper_client().search(query, num_results=3)


def render_visa_cards(nationality: str, destination: str) -> None:
    for icon, title, template in _CATEGORIES:
        query = template.format(nat=nationality, dst=destination)
        st.markdown(f"### {icon} {title}")
        try:
            results = _search(query)
        except ProviderError as exc:
            st.warning(str(exc))
            continue

        for r in results:
            st.markdown(
                f"""
                <div class="glass-card fade-in">
                    <div style="font-weight:700;">{r.title}</div>
                    <div style="color:var(--text-muted); opacity:0.85; font-size:0.92rem; margin-top:4px;">
                        {r.snippet}
                    </div>
                    <a href="{r.link}" target="_blank" style="font-size:0.85rem;">{r.link}</a>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.write("")
