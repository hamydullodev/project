"""Airport Search Tool: resolve airport/city names, IATA codes, metadata.

Backed by the Geoapify Geocoding + Places APIs (:mod:`app.api.geoapify`).
Handles both directions the PDF spec calls out: "TAS kodi qaysi
aeroportniki?" (lookup by IATA code) and "Istanbul aeroportlarini ko'rsat"
(lookup by city name).
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.api.exceptions import ProviderError
from app.api.geoapify import get_geoapify_client
from app.api.schemas import Airport
from app.utils.cache import cached
from app.utils.logger import get_logger

logger = get_logger(__name__)


@cached("airport_search")
def _search_by_city_impl(city: str) -> list[Airport]:
    return get_geoapify_client().search_airports_by_city(city)


@cached("airport_search")
def _search_by_iata_impl(iata_code: str) -> Airport | None:
    return get_geoapify_client().search_by_iata(iata_code)


def _format_airports(airports: list[Airport]) -> str:
    lines = []
    for a in airports:
        code = f" ({a.iata_code})" if a.iata_code else ""
        location = ", ".join(part for part in (a.city, a.country) if part)
        lines.append(f"- **{a.name}**{code} — {location}")
    return "\n".join(lines)


@tool
def search_airports(city_or_place: str) -> str:
    """Find airports in or near a city/place by free-text name.

    Args:
        city_or_place: A city, region, or place name, e.g. "Istanbul" or
            "Toshkent".
    """
    try:
        airports = _search_by_city_impl(city_or_place)
    except ProviderError as exc:
        logger.warning("search_airports failed: {}", exc)
        return f"⚠️ {exc}"
    return f"'{city_or_place}' atrofidagi aeroportlar:\n\n{_format_airports(airports)}"


@tool
def lookup_airport_by_code(iata_code: str) -> str:
    """Resolve a 3-letter IATA airport code to its name, city, and country.

    Args:
        iata_code: A 3-letter IATA airport code, e.g. "TAS".
    """
    try:
        airport = _search_by_iata_impl(iata_code)
    except ProviderError as exc:
        logger.warning("lookup_airport_by_code failed: {}", exc)
        return f"⚠️ {exc}"

    if airport is None:
        return f"⚠️ '{iata_code}' kodi bo'yicha aeroport topilmadi."

    location = ", ".join(part for part in (airport.city, airport.country) if part)
    return f"**{iata_code.upper()}** — {airport.name} ({location})"
