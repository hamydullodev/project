"""OpenWeatherMap client: destination weather lookup (bonus feature)."""

from __future__ import annotations

import requests

from app.api.exceptions import (
    AuthenticationError,
    NoResultsError,
    ProviderUnavailableError,
)
from app.api.schemas import WeatherInfo
from app.config import get_settings

_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


class OpenWeatherClient:
    """Thin wrapper around the OpenWeatherMap current-weather endpoint."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.openweather_api_key
        self._timeout = settings.http_timeout_seconds

    def get_weather(self, city: str) -> WeatherInfo:
        if not self._api_key:
            raise AuthenticationError(
                "OpenWeather API key sozlanmagan. .env fayliga OPENWEATHER_API_KEY qiymatini kiriting."
            )
        try:
            response = requests.get(
                _BASE_URL,
                params={
                    "q": city,
                    "appid": self._api_key,
                    "units": "metric",
                    "lang": "en",
                },
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise ProviderUnavailableError("Ob-havo API bilan bog'lanishda xatolik.") from exc

        if response.status_code == 401:
            raise AuthenticationError("OpenWeather API key noto'g'ri.")
        if response.status_code == 404:
            raise NoResultsError(f"'{city}' shahri uchun ob-havo topilmadi.")
        if not response.ok:
            raise ProviderUnavailableError(f"Ob-havo API xatosi (HTTP {response.status_code}).")

        payload = response.json()
        return WeatherInfo(
            city=city,
            temperature_celsius=float(payload["main"]["temp"]),
            condition=payload["weather"][0]["description"],
            humidity_percent=payload["main"].get("humidity"),
        )


_client: OpenWeatherClient | None = None


def get_openweather_client() -> OpenWeatherClient:
    global _client
    if _client is None:
        _client = OpenWeatherClient()
    return _client
