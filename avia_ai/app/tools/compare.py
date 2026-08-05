"""Flight Compare Tool: side-by-side comparison of two or more flights.

Operates only on :class:`~app.api.schemas.Flight` rows already returned by
:mod:`app.tools.flight_search` in the current conversation turn — it never
re-fetches or fabricates data, it just re-sorts/re-presents what the
Flight Search Tool already retrieved from the provider.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.agent.memory import get_last_flights
from app.utils.formatter import comparison_summary, flights_to_markdown_table
from app.utils.logger import get_logger

logger = get_logger(__name__)


@tool
def compare_flights(flight_numbers: list[str] | None = None, airlines: list[str] | None = None) -> str:
    """Compare flights from the most recent search by price, duration, stops.

    Args:
        flight_numbers: Optional list of flight numbers to restrict the
            comparison to (e.g. ["TK371", "HY101"]). If omitted, all flights
            from the last search are compared.
        airlines: Optional list of airline names/codes to restrict the
            comparison to (e.g. ["Turkish Airlines", "Uzbekistan Airways"]).
    """
    flights = get_last_flights()
    if not flights:
        return "⚠️ Taqqoslash uchun avval reys qidiring."

    if flight_numbers:
        wanted = {fn.lower() for fn in flight_numbers}
        flights = [f for f in flights if f.flight_number.lower() in wanted]
    if airlines:
        wanted = {a.lower() for a in airlines}
        flights = [f for f in flights if any(w in f.airline.lower() or w in f.airline_code.lower() for w in wanted)]

    if len(flights) < 2:
        return "⚠️ Taqqoslash uchun kamida 2 ta reys kerak."

    table = flights_to_markdown_table(flights)
    summary = comparison_summary(flights)
    return f"{table}\n\n{summary}"
