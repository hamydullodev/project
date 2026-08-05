"""LangGraph tool definitions.

Each module exposes one or more `@tool`-decorated callables that the LLM
can select via tool calling. Tools are thin orchestration layers: they
validate LLM-supplied arguments, delegate data retrieval to `app.api`,
and return structured, formatter-ready results. The LLM never fabricates
flight facts — every number surfaced to the user passes through one of
these tools.
"""

from app.tools.airport import lookup_airport_by_code, search_airports
from app.tools.compare import compare_flights
from app.tools.currency import convert_currency, convert_last_flight_prices
from app.tools.flight_search import search_flights
from app.tools.flight_status import get_flight_status
from app.tools.travel import recommend_flight
from app.tools.weather import get_destination_weather
from app.tools.web_search import recommend_destination_guide, web_search

ALL_TOOLS = [
    search_flights,
    compare_flights,
    search_airports,
    lookup_airport_by_code,
    convert_currency,
    convert_last_flight_prices,
    recommend_flight,
    get_destination_weather,
    get_flight_status,
    web_search,
    recommend_destination_guide,
]

__all__ = [
    "ALL_TOOLS",
    "search_flights",
    "compare_flights",
    "search_airports",
    "lookup_airport_by_code",
    "convert_currency",
    "convert_last_flight_prices",
    "recommend_flight",
    "get_destination_weather",
    "get_flight_status",
    "web_search",
    "recommend_destination_guide",
]
