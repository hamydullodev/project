"""Weather Tool (bonus): destination weather lookup for trip planning."""

from __future__ import annotations

from langchain_core.tools import tool

from app.api.exceptions import ProviderError
from app.api.openweather import get_openweather_client
from app.utils.cache import cached
from app.utils.logger import get_logger

logger = get_logger(__name__)


@cached("weather")
def _get_weather_impl(city: str):
    return get_openweather_client().get_weather(city)


@tool
def get_destination_weather(city: str) -> str:
    """Get the current weather for a destination city, for trip planning.

    Args:
        city: City name, e.g. "Istanbul".
    """
    try:
        weather = _get_weather_impl(city)
    except ProviderError as exc:
        logger.warning("get_destination_weather failed: {}", exc)
        return f"⚠️ {exc}"

    humidity = f", namlik {weather.humidity_percent}%" if weather.humidity_percent is not None else ""
    return f"{weather.city}: {weather.temperature_celsius:.0f}°C, {weather.condition}{humidity}"
