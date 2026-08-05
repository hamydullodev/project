"""Dispatch to whichever :class:`~app.config.FlightDataProvider` is active.

Tools call :func:`get_flight_provider_client` instead of importing a
specific client, so switching ``FLIGHT_DATA_PROVIDER`` in ``.env`` is the
only change needed to swap providers.
"""

from __future__ import annotations

from typing import Protocol

from app.api.schemas import Flight, FlightSearchQuery
from app.config import FlightDataProvider, get_settings


class FlightProviderClient(Protocol):
    def search_flights(self, query: FlightSearchQuery) -> list[Flight]: ...


def get_flight_provider_client() -> FlightProviderClient:
    """Return the client for the currently configured flight data provider."""
    provider = get_settings().flight_data_provider

    if provider is FlightDataProvider.AMADEUS:
        from app.api.amadeus import get_amadeus_client

        return get_amadeus_client()
    if provider is FlightDataProvider.AVIATIONSTACK:
        from app.api.aviationstack import get_aviationstack_client

        return get_aviationstack_client()
    if provider is FlightDataProvider.KIWI:
        raise NotImplementedError(
            "Kiwi Tequila client hali implement qilinmagan. FLIGHT_DATA_PROVIDER=amadeus yoki aviationstack qiling."
        )
    raise NotImplementedError(f"Noma'lum flight data provider: {provider}")
