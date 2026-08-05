"""AviationStack API client: real-time flight schedules and status.

AviationStack's ``/flights`` endpoint returns real departure/arrival
airports, times, airline, and flight number, but — even on paid tiers —
never a fare. Flights parsed here always have ``price=None``; the tool and
UI layers show "narx mavjud emas" instead of guessing a number, per the
project's hard rule against fabricating flight facts.
"""

from __future__ import annotations

from datetime import datetime

import requests

from app.api.exceptions import (
    AuthenticationError,
    InvalidRequestError,
    NoResultsError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.api.schemas import Flight, FlightSearchQuery
from app.config import get_settings


class AviationStackClient:
    """Thin wrapper around the AviationStack real-time flights endpoint."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.aviationstack_base_url.rstrip("/")
        self._api_key = settings.aviationstack_api_key
        self._timeout = settings.http_timeout_seconds

    def _ensure_credentials(self) -> None:
        if not self._api_key:
            raise AuthenticationError(
                "AviationStack API key sozlanmagan. .env fayliga AVIATIONSTACK_API_KEY qiymatini kiriting."
            )

    def _get(self, path: str, params: dict) -> dict:
        self._ensure_credentials()
        try:
            response = requests.get(
                f"{self._base_url}{path}",
                params={**params, "access_key": self._api_key},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise ProviderUnavailableError("AviationStack API bilan bog'lanishda xatolik.") from exc

        if response.status_code in (401, 403):
            raise AuthenticationError("AviationStack API key noto'g'ri.")
        if response.status_code == 429:
            raise RateLimitError("AviationStack so'rovlar chegarasiga yetdi.")
        if response.status_code == 422:
            raise InvalidRequestError("So'rov parametrlari noto'g'ri.")
        if response.status_code >= 500:
            raise ProviderUnavailableError("AviationStack serveri hozircha ishlamayapti.")
        if not response.ok:
            raise ProviderUnavailableError(f"AviationStack API xatosi (HTTP {response.status_code}).")

        payload = response.json()
        if "error" in payload:
            raise InvalidRequestError(payload["error"].get("message", "Noma'lum AviationStack xatosi."))
        return payload

    def search_flights(self, query: FlightSearchQuery) -> list[Flight]:
        """Search real (price-less) flight legs between two IATA airports.

        AviationStack's free tier rejects the ``flight_date`` filter
        (``function_access_restricted``) — it only serves the *current*
        real-time/scheduled flight board for a route. We fetch that board
        and filter to the requested date client-side, and are explicit
        with the user when the plan simply can't reach a future date.
        """
        params = {
            "dep_iata": query.origin.upper(),
            "arr_iata": query.destination.upper(),
            "limit": 100,
        }
        payload = self._get("/flights", params)
        all_legs = [self._parse_leg(leg) for leg in payload.get("data", []) if self._is_usable(leg)]

        flights = [f for f in all_legs if f.departure_time.strftime("%Y-%m-%d") == query.departure_date]
        if not flights:
            if all_legs:
                raise NoResultsError(
                    f"{query.origin} -> {query.destination} yo'nalishida {query.departure_date} "
                    "sanasida reys topilmadi. Eslatma: AviationStack bepul tarifi faqat joriy "
                    "kun jadvalini beradi — kelajakdagi sanalar uchun to'liq qo'llab-quvvatlanmaydi."
                )
            raise NoResultsError(f"{query.origin} -> {query.destination} yo'nalishida reys topilmadi.")
        return flights

    def get_status(self, flight_iata: str) -> Flight:
        """Look up the live/scheduled status of a single flight by its IATA number."""
        payload = self._get("/flights", {"flight_iata": flight_iata.upper(), "limit": 1})
        legs = [leg for leg in payload.get("data", []) if self._is_usable(leg)]
        if not legs:
            raise NoResultsError(f"'{flight_iata}' reysi bo'yicha ma'lumot topilmadi.")
        return self._parse_leg(legs[0])

    @staticmethod
    def _is_usable(leg: dict) -> bool:
        return bool(leg.get("departure", {}).get("scheduled") and leg.get("arrival", {}).get("scheduled"))

    @staticmethod
    def _parse_leg(leg: dict) -> Flight:
        departure = leg["departure"]
        arrival = leg["arrival"]
        airline = leg.get("airline", {})
        flight_info = leg.get("flight", {})

        dep_time = datetime.fromisoformat(departure["scheduled"])
        arr_time = datetime.fromisoformat(arrival["scheduled"])
        duration_minutes = max(0, int((arr_time - dep_time).total_seconds() // 60))

        return Flight(
            airline=airline.get("name") or airline.get("iata", "Noma'lum"),
            airline_code=airline.get("iata", ""),
            flight_number=flight_info.get("iata") or flight_info.get("number", ""),
            origin=departure.get("iata", ""),
            destination=arrival.get("iata", ""),
            departure_time=dep_time,
            arrival_time=arr_time,
            duration_minutes=duration_minutes,
            stops=0,
            cabin_class="",
            price=None,
            currency="",
            status=leg.get("flight_status", ""),
        )


_client: AviationStackClient | None = None


def get_aviationstack_client() -> AviationStackClient:
    global _client
    if _client is None:
        _client = AviationStackClient()
    return _client
