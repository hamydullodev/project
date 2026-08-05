"""Flight result card: airline, price/duration, expandable details, and an
honest external action button.

There's no booking backend in this project, so the action button doesn't
pretend to reserve a seat — it opens a real Google Flights search for the
same route/date/airline in a new tab, clearly labeled as such.
"""

from __future__ import annotations

from urllib.parse import quote

import streamlit as st

from app.api.schemas import Flight
from app.utils.formatter import format_duration, format_price


def _google_flights_url(flight: Flight) -> str:
    query = f"Flights from {flight.origin} to {flight.destination} on {flight.departure_time:%Y-%m-%d} {flight.airline}"
    return f"https://www.google.com/travel/flights?q={quote(query)}"


def render_flight_card(flight: Flight, *, key: str) -> None:
    """Render a single flight offer as a card with expandable details."""
    st.markdown(
        f"""
        <div class="glass-card fade-in">
            <div style="display:flex; justify-content:space-between; align-items:baseline;">
                <span style="font-size:1.05rem; font-weight:700;">
                    ✈️ {flight.airline} · {flight.flight_number}
                </span>
                <span class="gradient-text" style="font-size:1.1rem;">
                    {format_price(flight.price, flight.currency)}
                </span>
            </div>
            <div style="margin-top:6px; color:var(--text-muted); opacity:0.75; font-size:0.9rem;">
                {flight.origin} {flight.departure_time:%H:%M} → {flight.destination} {flight.arrival_time:%H:%M}
                &nbsp;·&nbsp; {flight.duration_label} &nbsp;·&nbsp; {flight.stops_label}
                &nbsp;·&nbsp; {flight.cabin_class or flight.status or "-"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Batafsil"):
        col1, col2 = st.columns(2)
        col1.markdown(
            f"**Jo'nash:** {flight.origin}, {flight.departure_time:%Y-%m-%d %H:%M}\n\n"
            f"**Yetib borish:** {flight.destination}, {flight.arrival_time:%H:%M}\n\n"
            f"**Davomiyligi:** {format_duration(flight.duration_minutes)}"
        )
        col2.markdown(
            f"**To'xtashlar:** {flight.stops_label}\n\n"
            f"**Klass:** {flight.cabin_class or '-'}\n\n"
            f"**Holati:** {flight.status or '-'}"
        )
        st.link_button(
            "🔗 Google Flights'da ko'rish",
            _google_flights_url(flight),
            use_container_width=True,
        )


def render_flight_cards(flights: list[Flight]) -> None:
    """Render a list of flights as stacked cards, or an empty-state hint."""
    if not flights:
        st.info(
            "Hali reys qidirilmagan. Chatga so'rov yozing, masalan: "
            '"Toshkentdan Istanbulga 15-avgust kuni uchadigan reyslarni top."'
        )
        return
    for i, flight in enumerate(flights):
        render_flight_card(flight, key=str(i))
