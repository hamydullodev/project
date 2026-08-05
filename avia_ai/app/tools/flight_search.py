"""Flight Search Tool: natural language -> provider API query -> flights.

The LLM never invents flight facts. It only decides *which* parameters to
pass here; every field returned (price, duration, airline, ...) comes from
the active :class:`~app.config.FlightDataProvider`.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.agent.memory import set_last_search
from app.api.exceptions import ProviderError
from app.api.provider import get_flight_provider_client
from app.api.schemas import Flight, FlightSearchQuery
from app.utils.cache import cached
from app.utils.formatter import flights_to_markdown_table
from app.utils.logger import get_logger
from app.utils.validators import InvalidInputError, validate_date, validate_iata_code

logger = get_logger(__name__)

_TIME_WINDOWS = {
    "morning": (5, 12),
    "ertalab": (5, 12),
    "afternoon": (12, 17),
    "kunduzi": (12, 17),
    "evening": (17, 21),
    "kechqurun": (17, 21),
    "night": (21, 5),
    "tun": (21, 5),
}


@cached("flight_search")
def _search_flights_impl(query: FlightSearchQuery) -> list[Flight]:
    """Fetch flights from the active provider and apply LLM-requested filters."""
    client = get_flight_provider_client()
    flights = client.search_flights(query)

    if query.max_stops is not None:
        flights = [f for f in flights if f.stops <= query.max_stops]
    if query.airline:
        wanted = query.airline.lower()
        flights = [f for f in flights if wanted in f.airline.lower() or wanted in f.airline_code.lower()]
    if query.time_of_day and query.time_of_day.lower() in _TIME_WINDOWS:
        start, end = _TIME_WINDOWS[query.time_of_day.lower()]
        if start < end:
            flights = [f for f in flights if start <= f.departure_time.hour < end]
        else:  # night window wraps past midnight
            flights = [f for f in flights if f.departure_time.hour >= start or f.departure_time.hour < end]

    sort_key = {
        "price": lambda f: (f.price is None, f.price or 0.0),
        "duration": lambda f: f.duration_minutes,
        "departure_time": lambda f: f.departure_time,
    }.get(query.sort_by or "", lambda f: f.departure_time)
    return sorted(flights, key=sort_key)


@tool
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    children: int = 0,
    return_date: str | None = None,
    cabin_class: str | None = None,
    max_stops: int | None = None,
    airline: str | None = None,
    time_of_day: str | None = None,
    sort_by: str | None = None,
) -> str:
    """Search real flight offers between two airports/cities on a given date.

    Args:
        origin: Origin airport IATA code (e.g. "TAS").
        destination: Destination airport IATA code (e.g. "IST").
        departure_date: Departure date, format YYYY-MM-DD.
        adults: Number of adult passengers.
        children: Number of child passengers.
        return_date: Optional return date, format YYYY-MM-DD.
        cabin_class: Optional cabin ("economy", "business", ...).
        max_stops: Optional maximum number of stops (0 = direct only).
        airline: Optional airline name/code filter, e.g. "Turkish Airlines".
        time_of_day: Optional departure window: "morning", "afternoon",
            "evening", or "night".
        sort_by: Optional sort order: "price", "duration", or "departure_time".
    """
    try:
        origin_code = validate_iata_code(origin)
        destination_code = validate_iata_code(destination)
        departure = validate_date(departure_date, field_name="jo'nash sanasi")
        return_ = validate_date(return_date, field_name="qaytish sanasi") if return_date else None

        query = FlightSearchQuery(
            origin=origin_code,
            destination=destination_code,
            departure_date=departure,
            return_date=return_,
            adults=adults,
            children=children,
            cabin_class=cabin_class,
            max_stops=max_stops,
            airline=airline,
            time_of_day=time_of_day,
            sort_by=sort_by,
        )
        flights = _search_flights_impl(query)
        set_last_search(query, flights)
    except (InvalidInputError, ProviderError) as exc:
        logger.warning("search_flights failed: {}", exc)
        return f"⚠️ {exc}"

    return (
        f"{origin_code} -> {destination_code} ({departure}) uchun {len(flights)} ta reys topildi:\n\n"
        + flights_to_markdown_table(flights)
    )
