"""Geoapify API client: powers the Airport Search Tool.

Geoapify has no dedicated "airport database" endpoint, so airport lookup is
composed from two of its APIs:

1. Geocoding — resolve a free-text place name ("Istanbul") to coordinates.
2. Places — find POIs tagged ``airport`` / ``airport.international`` near
   those coordinates (or near a raw lat/lon), including the OSM ``iata``
   tag when the data source has it.

This is the only module allowed to call ``api.geoapify.com`` directly.
"""

from __future__ import annotations

import requests

from app.api.exceptions import (
    AuthenticationError,
    InvalidRequestError,
    NoResultsError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.api.schemas import Airport
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GeoapifyClient:
    """Thin wrapper around Geoapify's Geocoding and Places APIs."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.geoapify_base_url.rstrip("/")
        self._api_key = settings.geoapify_api_key
        self._timeout = settings.http_timeout_seconds

    def _ensure_credentials(self) -> None:
        if not self._api_key:
            raise AuthenticationError("Geoapify API key sozlanmagan. .env fayliga GEOAPIFY_API_KEY qiymatini kiriting.")

    def _get(self, path: str, params: dict) -> dict:
        self._ensure_credentials()
        try:
            response = requests.get(
                f"{self._base_url}{path}",
                params={**params, "apiKey": self._api_key},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise ProviderUnavailableError("Geoapify API bilan bog'lanishda xatolik.") from exc

        if response.status_code == 401:
            raise AuthenticationError("Geoapify API key noto'g'ri.")
        if response.status_code == 429:
            raise RateLimitError("Geoapify so'rovlar chegarasiga yetdi.")
        if response.status_code == 400:
            raise InvalidRequestError("So'rov parametrlari noto'g'ri.")
        if response.status_code >= 500:
            raise ProviderUnavailableError("Geoapify serveri hozircha ishlamayapti.")
        if not response.ok:
            raise ProviderUnavailableError(f"Geoapify API xatosi (HTTP {response.status_code}).")

        return response.json()

    def geocode(self, place: str) -> tuple[float, float] | None:
        """Resolve a free-text place name to (latitude, longitude)."""
        payload = self._get(
            "/v1/geocode/search",
            {"text": place, "limit": 1, "type": "city"},
        )
        features = payload.get("features", [])
        if not features:
            return None
        lon, lat = features[0]["geometry"]["coordinates"]
        return lat, lon

    def search_airports_by_city(self, city: str, radius_km: int = 60) -> list[Airport]:
        """Find airports near a free-text city/place name."""
        coords = self.geocode(city)
        if coords is None:
            raise NoResultsError(f"'{city}' nomli joy topilmadi.")
        return self.search_airports_near(*coords, radius_km=radius_km)

    def search_airports_near(self, latitude: float, longitude: float, radius_km: int = 60) -> list[Airport]:
        """Find airports within ``radius_km`` of a coordinate."""
        payload = self._get(
            "/v2/places",
            {
                "categories": "airport",
                "filter": f"circle:{longitude},{latitude},{radius_km * 1000}",
                "bias": f"proximity:{longitude},{latitude}",
                "limit": 20,
            },
        )
        airports = [self._parse_feature(feature) for feature in payload.get("features", [])]
        if not airports:
            raise NoResultsError("Berilgan joy atrofida aeroport topilmadi.")
        return airports

    def search_by_iata(self, iata_code: str) -> Airport | None:
        """Best-effort lookup of an airport by its IATA code via text search."""
        payload = self._get(
            "/v1/geocode/search",
            {"text": f"{iata_code} airport", "limit": 5, "type": "amenity"},
        )
        for feature in payload.get("features", []):
            props = feature.get("properties", {})
            raw = props.get("datasource", {}).get("raw", {})
            if str(raw.get("iata", "")).upper() == iata_code.upper():
                return self._parse_feature(feature)
        return None

    @staticmethod
    def _parse_feature(feature: dict) -> Airport:
        props = feature.get("properties", {})
        raw = props.get("datasource", {}).get("raw", {})
        lon, lat = feature["geometry"]["coordinates"]
        return Airport(
            iata_code=str(raw.get("iata", "") or "").upper(),
            name=props.get("name") or raw.get("name", "Noma'lum aeroport"),
            city=props.get("city", "") or props.get("county", ""),
            country=props.get("country", ""),
            latitude=lat,
            longitude=lon,
        )


_client: GeoapifyClient | None = None


def get_geoapify_client() -> GeoapifyClient:
    """Return a process-wide :class:`GeoapifyClient` singleton."""
    global _client
    if _client is None:
        _client = GeoapifyClient()
    return _client
