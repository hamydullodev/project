"""Serper (Google Search) API client: general web search (bonus feature).

Used for questions outside the other providers' domain — visa
requirements, city info, travel advisories — never as a source of flight
prices or schedules; those must always come through the Flight Search Tool.
"""

from __future__ import annotations

import requests

from app.api.exceptions import (
    AuthenticationError,
    NoResultsError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.api.schemas import WebSearchResult
from app.config import get_settings


class SerperClient:
    """Thin wrapper around the Serper `/search` endpoint."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.serper_base_url.rstrip("/")
        self._api_key = settings.serper_api_key
        self._timeout = settings.http_timeout_seconds

    def search(self, query: str, num_results: int = 5) -> list[WebSearchResult]:
        if not self._api_key:
            raise AuthenticationError("Serper API key sozlanmagan. .env fayliga SERPER_API_KEY qiymatini kiriting.")
        try:
            response = requests.post(
                f"{self._base_url}/search",
                json={"q": query, "num": num_results},
                headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise ProviderUnavailableError("Serper API bilan bog'lanishda xatolik.") from exc

        if response.status_code in (401, 403):
            raise AuthenticationError("Serper API key noto'g'ri.")
        if response.status_code == 429:
            raise RateLimitError("Serper so'rovlar chegarasiga yetdi.")
        if not response.ok:
            raise ProviderUnavailableError(f"Serper API xatosi (HTTP {response.status_code}).")

        payload = response.json()
        results = [
            WebSearchResult(
                title=item.get("title", ""),
                link=item.get("link", ""),
                snippet=item.get("snippet", ""),
            )
            for item in payload.get("organic", [])[:num_results]
        ]
        if not results:
            raise NoResultsError(f"'{query}' bo'yicha qidiruv natijasi topilmadi.")
        return results


_client: SerperClient | None = None


def get_serper_client() -> SerperClient:
    global _client
    if _client is None:
        _client = SerperClient()
    return _client
