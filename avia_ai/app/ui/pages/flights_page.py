"""Reys natijalari: sort/filter controls over the most recent search."""

from __future__ import annotations

import streamlit as st

from app.agent.memory import get_last_flights
from app.ui.components.cards import render_flight_cards

_SORT_OPTIONS = {
    "Narx (arzondan)": lambda f: (f.price is None, f.price or 0.0),
    "Davomiylik (tezdan)": lambda f: f.duration_minutes,
    "Jo'nash vaqti": lambda f: f.departure_time,
}


def render() -> None:
    st.markdown("## 🛫 Reys natijalari")

    flights = get_last_flights()
    if not flights:
        render_flight_cards(flights)
        return

    airlines = sorted({f.airline for f in flights})

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        sort_label = st.selectbox("Saralash", list(_SORT_OPTIONS.keys()))
    with col2:
        chosen_airlines = st.multiselect("Aviakompaniya", airlines, default=airlines)
    with col3:
        direct_only = st.checkbox("Faqat to'g'ridan-to'g'ri")

    filtered = [f for f in flights if f.airline in chosen_airlines]
    if direct_only:
        filtered = [f for f in filtered if f.stops == 0]
    filtered.sort(key=_SORT_OPTIONS[sort_label])

    st.caption(f"{len(filtered)} / {len(flights)} reys ko'rsatilmoqda")
    render_flight_cards(filtered)
