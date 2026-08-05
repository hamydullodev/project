"""Flight comparison DataGrid component: sort, filter, best-value highlight."""

from __future__ import annotations

import streamlit as st

from app.api.schemas import Flight
from app.utils.formatter import flights_to_dataframe


def render_comparison(flights: list[Flight]) -> None:
    """Render flights in a sortable table, highlighting the best-value row."""
    if not flights:
        st.info("Taqqoslash uchun kamida 2 ta reys kerak. Avval chatda qidiring.")
        return
    if len(flights) < 2:
        st.warning("Faqat 1 ta reys mavjud — taqqoslash uchun yana qidiring.")

    df = flights_to_dataframe(flights)
    priced = [f for f in flights if f.has_price]
    fastest_idx = min(range(len(flights)), key=lambda i: flights[i].duration_minutes)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if priced:
            cheapest = min(priced, key=lambda f: f.price)
            st.markdown(f"💰 **Eng arzon:** {cheapest.airline} {cheapest.flight_number}")
        else:
            st.markdown("💰 **Narx:** bu provayder taqdim etmaydi")
    with col2:
        st.markdown(f"⚡ **Eng tez:** {flights[fastest_idx].airline} {flights[fastest_idx].flight_number}")
