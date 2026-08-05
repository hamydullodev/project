"""Response formatting helpers: tables, markdown, currency/duration display.

Kept separate from the tools/agent layer so the same rendering logic can be
reused by the Streamlit UI (dataframes) and by the LLM-facing tool output
(markdown tables in chat).
"""

from __future__ import annotations

import pandas as pd

from app.api.schemas import Flight


def format_price(amount: float | None, currency: str) -> str:
    if amount is None:
        return "narx mavjud emas"
    return f"{amount:,.2f} {currency}"


def format_duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m"


def flights_to_dataframe(flights: list[Flight]) -> pd.DataFrame:
    """Convert flights into a UI/markdown-ready table."""
    rows = [
        {
            "Aviakompaniya": f.airline,
            "Reys": f.flight_number,
            "Jo'nash": f"{f.origin} {f.departure_time:%H:%M}",
            "Yetib borish": f"{f.destination} {f.arrival_time:%H:%M}",
            "Sana": f.departure_time.strftime("%Y-%m-%d"),
            "Davomiyligi": f.duration_label,
            "To'xtashlar": f.stops_label,
            "Klass": f.cabin_class or "-",
            "Narx": format_price(f.price, f.currency),
            "Holati": f.status or "-",
        }
        for f in flights
    ]
    return pd.DataFrame(rows)


def flights_to_markdown_table(flights: list[Flight]) -> str:
    """Render flights as a markdown table for chat display."""
    if not flights:
        return "_Reyslar topilmadi._"
    df = flights_to_dataframe(flights)
    return df.to_markdown(index=False)


def comparison_summary(flights: list[Flight]) -> str:
    """One-line natural-language summary highlighting cheapest/fastest."""
    if not flights:
        return "Taqqoslash uchun reys yo'q."

    fastest = min(flights, key=lambda f: f.duration_minutes)
    lines = [
        f"⚡ Eng tez: **{fastest.airline} {fastest.flight_number}** — {format_duration(fastest.duration_minutes)}",
    ]

    priced = [f for f in flights if f.has_price]
    if priced:
        cheapest = min(priced, key=lambda f: f.price)
        lines.insert(
            0,
            f"💰 Eng arzon: **{cheapest.airline} {cheapest.flight_number}** — "
            f"{format_price(cheapest.price, cheapest.currency)}",
        )
    else:
        lines.insert(0, "💰 Bu provayder narx ma'lumotini taqdim etmaydi.")
    return "\n".join(lines)
