"""Travel Recommendation Tool: cheapest / fastest / family / business, etc.

Picks one flight out of the most recent search result according to a
natural-language criterion the LLM has already normalized (e.g. "eng
arzoni", "eng tezi", "to'g'ridan-to'g'ri"). It never invents a flight that
wasn't in the search results.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.agent.memory import get_last_flights
from app.utils.formatter import format_duration, format_price
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _price_key(f):
    return (f.price is None, f.price or 0.0)


_CRITERIA = {
    "cheapest": _price_key,
    "arzon": _price_key,
    "fastest": lambda f: f.duration_minutes,
    "tez": lambda f: f.duration_minutes,
    "direct": lambda f: (f.stops, *_price_key(f)),
    "togridan": lambda f: (f.stops, *_price_key(f)),
}


@tool
def recommend_flight(criteria: str = "cheapest") -> str:
    """Recommend one flight from the most recent search result.

    Args:
        criteria: What to optimize for: "cheapest", "fastest", or "direct".
    """
    flights = get_last_flights()
    if not flights:
        return "⚠️ Tavsiya berish uchun avval reys qidiring."

    key = next((fn for name, fn in _CRITERIA.items() if name in criteria.lower()), None)
    if key is None:
        key = _CRITERIA["cheapest"]

    best = min(flights, key=key)
    return (
        f"✅ Tavsiya: **{best.airline} {best.flight_number}**\n"
        f"- Jo'nash: {best.origin} {best.departure_time:%Y-%m-%d %H:%M}\n"
        f"- Yetib borish: {best.destination} {best.arrival_time:%H:%M}\n"
        f"- Davomiyligi: {format_duration(best.duration_minutes)} | {best.stops_label}\n"
        f"- Narx: {format_price(best.price, best.currency)}"
    )
