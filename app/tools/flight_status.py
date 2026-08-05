"""Flight Status Tool (bonus): live/scheduled status for a specific flight.

Uses AviationStack directly (regardless of the active
``FLIGHT_DATA_PROVIDER``) since it's the provider with real-time status
data among the ones configured in this project.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.api.aviationstack import get_aviationstack_client
from app.api.exceptions import ProviderError
from app.utils.cache import cached
from app.utils.formatter import format_duration
from app.utils.logger import get_logger

logger = get_logger(__name__)


@cached("flight_status")
def _get_status_impl(flight_iata: str):
    return get_aviationstack_client().get_status(flight_iata)


@tool
def get_flight_status(flight_iata: str) -> str:
    """Get the live/scheduled status of a specific flight by its IATA number.

    Args:
        flight_iata: IATA flight number, e.g. "HY123" or "TK371".
    """
    try:
        flight = _get_status_impl(flight_iata)
    except ProviderError as exc:
        logger.warning("get_flight_status failed: {}", exc)
        return f"⚠️ {exc}"

    status = flight.status or "noma'lum"
    return (
        f"**{flight.flight_number}** ({flight.airline}) — holati: **{status}**\n"
        f"{flight.origin} {flight.departure_time:%Y-%m-%d %H:%M} -> "
        f"{flight.destination} {flight.arrival_time:%H:%M} "
        f"({format_duration(flight.duration_minutes)})"
    )
