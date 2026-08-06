"""Hero shown when the chat is empty: logo icon, title, subtitle, disclaimer,
and a handful of example-query chips so users know what to ask.
"""

from __future__ import annotations

import streamlit as st

DISCLAIMER = (
    "Ushbu platforma tashxis qo'ymaydi va davolash usulini tavsiya qilmaydi. "
    "Iltimos, malakali shifokorga murojaat qiling."
)

EXAMPLES = [
    "Eng arzon Vitamin D3",
    "100 000 so'mgacha Omega-3 top",
    "Paracetamol 500mg",
    "Bolalar uchun yo'tal siropi",
]


def render_hero() -> str | None:
    """Render the empty-state hero. Returns an example query if the user
    clicked a suggestion chip, else None."""
    st.markdown(
        f"""
        <div class="hero-wrap fade-in">
            <div class="hero-icon">💊</div>
            <div class="hero-title">AI Pharmacy</div>
            <div class="hero-subtitle">
                O'zbekiston dorixonalaridan dori-darmonlarni AI yordamida bir zumda toping.<br/>
                Narxlarni, mavjudlikni va dorixonalarni soniyalarda solishtiring.
            </div>
            <div class="hero-disclaimer">⚕️ {DISCLAIMER}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    clicked = None
    cols = st.columns(len(EXAMPLES))
    for col, example in zip(cols, EXAMPLES):
        with col:
            if st.button(example, key=f"hero_ex_{example}", use_container_width=True):
                clicked = example
    return clicked
