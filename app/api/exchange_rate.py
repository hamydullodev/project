"""ExchangeRate-API client: live currency conversion rates (bonus feature)."""

from __future__ import annotations

import requests

from app.api.exceptions import (
    AuthenticationError,
    InvalidRequestError,
    ProviderUnavailableError,
)
from app.api.schemas import CurrencyRate
from app.config import get_settings


class ExchangeRateClient:
    """Thin wrapper around the exchangerate-api.com v6 API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.exchange_rate_base_url.rstrip("/")
        self._api_key = settings.exchange_rate_api_key
        self._timeout = settings.http_timeout_seconds

    def get_rate(self, base_currency: str, target_currency: str) -> CurrencyRate:
        if not self._api_key:
            raise AuthenticationError(
                "Exchange rate API key sozlanmagan. .env fayliga EXCHANGE_RATE_API_KEY qiymatini kiriting."
            )
        try:
            response = requests.get(
                f"{self._base_url}/{self._api_key}/pair/{base_currency}/{target_currency}",
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise ProviderUnavailableError("Kurs API bilan bog'lanishda xatolik.") from exc

        if response.status_code == 401 or response.status_code == 403:
            raise AuthenticationError("Exchange rate API key noto'g'ri.")
        if not response.ok:
            raise ProviderUnavailableError(f"Kurs API xatosi (HTTP {response.status_code}).")

        payload = response.json()
        if payload.get("result") != "success":
            raise InvalidRequestError(f"'{base_currency}' -> '{target_currency}' kursi topilmadi.")
        return CurrencyRate(
            base_currency=base_currency.upper(),
            target_currency=target_currency.upper(),
            rate=float(payload["conversion_rate"]),
        )


_client: ExchangeRateClient | None = None


def get_exchange_rate_client() -> ExchangeRateClient:
    global _client
    if _client is None:
        _client = ExchangeRateClient()
    return _client
