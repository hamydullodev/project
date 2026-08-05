"""Web Search Tool (bonus): general travel info via Google Search (Serper).

For questions the other tools can't answer — visa requirements, safety
advisories, city info. Not a flight-data source: the system prompt tells
the LLM to use the Flight Search Tool for anything price/schedule related.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.api.exceptions import ProviderError
from app.api.serper import get_serper_client
from app.utils.cache import cached
from app.utils.logger import get_logger

logger = get_logger(__name__)


@cached("web_search")
def _search_impl(query: str):
    return get_serper_client().search(query)


@tool
def web_search(query: str) -> str:
    """Search the web for general travel info not covered by other tools:
    visa requirements, safety advisories, local customs, city guides, etc.
    Do NOT use this for flight prices or schedules — use search_flights.

    Args:
        query: The search query, e.g. "Uzbekistan fuqarolari uchun Turkiya vizasi".
    """
    try:
        results = _search_impl(query)
    except ProviderError as exc:
        logger.warning("web_search failed: {}", exc)
        return f"⚠️ {exc}"

    lines = [f"- **{r.title}**: {r.snippet} ({r.link})" for r in results]
    return "\n".join(lines)


@tool
def recommend_destination_guide(city: str) -> str:
    """Recommend well-known tourist attractions and hotels for a destination
    city, with real sources — for travelers who already found their flight
    and want vacation ideas. Runs two live web searches (attractions,
    hotels) rather than inventing place/hotel names.

    Args:
        city: Destination city, e.g. "Istanbul".
    """
    try:
        attractions = _search_impl(f"{city} eng mashhur sayohat joylari diqqatga sazovor")
        hotels = _search_impl(f"{city} eng yaxshi mehmonxonalar tavsiya")
    except ProviderError as exc:
        logger.warning("recommend_destination_guide failed: {}", exc)
        return f"⚠️ {exc}"

    attraction_lines = [f"- **{r.title}**: {r.snippet} ({r.link})" for r in attractions]
    hotel_lines = [f"- **{r.title}**: {r.snippet} ({r.link})" for r in hotels]
    return (
        f"📍 {city} — diqqatga sazovor joylar:\n"
        + "\n".join(attraction_lines)
        + f"\n\n🏨 {city} — tavsiya etilgan mehmonxonalar:\n"
        + "\n".join(hotel_lines)
    )
