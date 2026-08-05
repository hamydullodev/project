"""Amadeus API client: OAuth2 auth, flight search, retry/error handling.

This is the active :class:`app.config.FlightDataProvider.AMADEUS` client.
It is the only place in the codebase allowed to talk to Amadeus directly —
tools call :func:`search_flights`, never ``requests``.
"""

from __future__ import annotations

import time
from datetime import datetime

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.api.exceptions import (
    AuthenticationError,
    InvalidRequestError,
    NoResultsError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.api.schemas import Flight, FlightSearchQuery
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_CABIN_MAP = {
    "economy": "ECONOMY",
    "premium_economy": "PREMIUM_ECONOMY",
    "business": "BUSINESS",
    "first": "FIRST",
}


class AmadeusClient:
    """Thin wrapper around the Amadeus self-service flight-offers API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.amadeus_base_url.rstrip("/")
        self._api_key = settings.amadeus_api_key
        self._api_secret = settings.amadeus_api_secret
        self._max_retries = settings.http_max_retries
        self._backoff = settings.http_backoff_seconds
        self._timeout = settings.http_timeout_seconds
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def _ensure_credentials(self) -> None:
        if not (self._api_key and self._api_secret):
            raise AuthenticationError(
                "Amadeus API key/secret sozlanmagan. .env fayliga "
                "AMADEUS_API_KEY va AMADEUS_API_SECRET qiymatlarini kiriting."
            )

    def _get_access_token(self) -> str:
        self._ensure_credentials()
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        try:
            response = requests.post(
                f"{self._base_url}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._api_key,
                    "client_secret": self._api_secret,
                },
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise ProviderUnavailableError("Amadeus autentifikatsiya serveriga ulanib bo'lmadi.") from exc

        if response.status_code == 401:
            raise AuthenticationError("Amadeus API key/secret noto'g'ri.")
        if not response.ok:
            raise ProviderUnavailableError(f"Amadeus autentifikatsiya xatosi (HTTP {response.status_code}).")

        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.monotonic() + int(payload.get("expires_in", 1800)) - 30
        return self._token

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=1, max=10),
        retry=retry_if_exception_type(ProviderUnavailableError),
    )
    def _get(self, path: str, params: dict) -> dict:
        token = self._get_access_token()
        try:
            response = requests.get(
                f"{self._base_url}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise ProviderUnavailableError("Amadeus API bilan bog'lanishda xatolik.") from exc

        if response.status_code == 401:
            self._token = None
            raise AuthenticationError("Amadeus token yaroqsiz yoki muddati o'tgan.")
        if response.status_code == 429:
            raise RateLimitError("Amadeus so'rovlar chegarasiga yetdi. Birozdan so'ng qayta urinib ko'ring.")
        if response.status_code == 400:
            detail = response.json().get("errors", [{}])[0].get("detail", "")
            raise InvalidRequestError(detail or "So'rov parametrlari noto'g'ri.")
        if response.status_code >= 500:
            raise ProviderUnavailableError("Amadeus serveri hozircha ishlamayapti.")
        if not response.ok:
            raise ProviderUnavailableError(f"Amadeus API xatosi (HTTP {response.status_code}).")

        return response.json()

    def search_flights(self, query: FlightSearchQuery) -> list[Flight]:
        """Search flight offers and return normalized :class:`Flight` rows."""
        params: dict = {
            "originLocationCode": query.origin.upper(),
            "destinationLocationCode": query.destination.upper(),
            "departureDate": query.departure_date,
            "adults": query.adults,
            "currencyCode": "USD",
            "max": 20,
        }
        if query.children:
            params["children"] = query.children
        if query.return_date:
            params["returnDate"] = query.return_date
        if query.cabin_class:
            params["travelClass"] = _CABIN_MAP.get(query.cabin_class.lower(), query.cabin_class.upper())

        payload = self._get("/v2/shopping/flight-offers", params)
        offers = payload.get("data", [])
        dictionaries = payload.get("dictionaries", {})
        carriers = dictionaries.get("carriers", {})

        flights = [self._parse_offer(offer, carriers) for offer in offers]
        if not flights:
            raise NoResultsError(
                f"{query.origin} -> {query.destination} yo'nalishida {query.departure_date} sanasida reys topilmadi."
            )
        return flights

    @staticmethod
    def _parse_offer(offer: dict, carriers: dict) -> Flight:
        itinerary = offer["itineraries"][0]
        segments = itinerary["segments"]
        first_segment, last_segment = segments[0], segments[-1]
        carrier_code = first_segment["carrierCode"]

        duration = itinerary["duration"]  # e.g. "PT3H25M"
        duration_minutes = _parse_iso8601_duration(duration)

        price = offer["price"]
        cabin = offer.get("travelerPricings", [{}])[0].get("fareDetailsBySegment", [{}])[0].get("cabin", "ECONOMY")

        return Flight(
            airline=carriers.get(carrier_code, carrier_code),
            airline_code=carrier_code,
            flight_number=f"{carrier_code}{first_segment['number']}",
            origin=first_segment["departure"]["iataCode"],
            destination=last_segment["arrival"]["iataCode"],
            departure_time=datetime.fromisoformat(first_segment["departure"]["at"]),
            arrival_time=datetime.fromisoformat(last_segment["arrival"]["at"]),
            duration_minutes=duration_minutes,
            stops=len(segments) - 1,
            cabin_class=cabin,
            price=float(price["total"]),
            currency=price["currency"],
        )


def _parse_iso8601_duration(value: str) -> int:
    """Parse an ISO-8601 duration like ``PT3H25M`` into total minutes."""
    hours = minutes = 0
    body = value.removeprefix("PT")
    if "H" in body:
        hours_part, body = body.split("H", 1)
        hours = int(hours_part)
    if "M" in body:
        minutes_part = body.split("M", 1)[0]
        minutes = int(minutes_part)
    return hours * 60 + minutes


_client: AmadeusClient | None = None


def get_amadeus_client() -> AmadeusClient:
    """Return a process-wide :class:`AmadeusClient` singleton."""
    global _client
    if _client is None:
        _client = AmadeusClient()
    return _client
