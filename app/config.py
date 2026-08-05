"""Centralized application configuration.

All runtime configuration is declared here as a single, strongly-typed
``Settings`` object backed by Pydantic Settings. Values are sourced from
environment variables / a local ``.env`` file, never hard-coded in the
business logic. Every other module in the codebase must read configuration
through :func:`get_settings` rather than calling ``os.getenv`` directly —
this keeps configuration access centralized, typed, and testable (a module
under test can monkeypatch ``get_settings`` instead of the environment).
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR: Path = Path(__file__).resolve().parent.parent
LOGS_DIR: Path = BASE_DIR / "logs"
ASSETS_DIR: Path = BASE_DIR / "assets"


class FlightDataProvider(str, Enum):
    """Supported third-party flight data providers.

    Exactly one provider is active at a time, selected via the
    ``FLIGHT_DATA_PROVIDER`` environment variable. The active provider is
    the sole source of truth for flight facts — the LLM never fabricates
    flight data, it only queries a provider through a tool call.
    """

    AMADEUS = "amadeus"
    KIWI = "kiwi"
    AVIATIONSTACK = "aviationstack"


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Instances are immutable snapshots of the environment at process start.
    Use :func:`get_settings` to obtain the process-wide singleton instead
    of instantiating this class directly.
    """

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---------------------------------------------------
    app_name: str = Field(default="Avia AI", alias="APP_NAME")
    app_env: Literal["development", "production"] = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO", alias="LOG_LEVEL")

    # --- Local LLM (Ollama) ----------------------------------------------
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2:3b-instruct-q4_K_M", alias="OLLAMA_MODEL")
    ollama_temperature: float = Field(default=0.3, alias="OLLAMA_TEMPERATURE")
    ollama_request_timeout_seconds: int = Field(default=60, alias="OLLAMA_REQUEST_TIMEOUT_SECONDS")

    # --- Speech-to-Text (local Whisper, no cloud API) ----------------------
    whisper_model_size: str = Field(default="small", alias="WHISPER_MODEL_SIZE")
    whisper_language: str = Field(default="uz", alias="WHISPER_LANGUAGE")

    # --- Flight Data Provider ---------------------------------------------
    flight_data_provider: FlightDataProvider = Field(default=FlightDataProvider.AMADEUS, alias="FLIGHT_DATA_PROVIDER")
    amadeus_api_key: str = Field(default="", alias="AMADEUS_API_KEY")
    amadeus_api_secret: str = Field(default="", alias="AMADEUS_API_SECRET")
    amadeus_base_url: str = Field(default="https://test.api.amadeus.com", alias="AMADEUS_BASE_URL")
    kiwi_tequila_api_key: str = Field(default="", alias="KIWI_TEQUILA_API_KEY")
    aviationstack_api_key: str = Field(default="", alias="AVIATIONSTACK_API_KEY")
    aviationstack_base_url: str = Field(default="http://api.aviationstack.com/v1", alias="AVIATIONSTACK_BASE_URL")

    # --- Airport / Places Search (Geoapify) ---------------------------------
    geoapify_api_key: str = Field(default="", alias="GEOAPIFY_API_KEY")
    geoapify_base_url: str = Field(default="https://api.geoapify.com", alias="GEOAPIFY_BASE_URL")

    # --- Currency Exchange -------------------------------------------------
    exchange_rate_api_key: str = Field(default="", alias="EXCHANGE_RATE_API_KEY")
    exchange_rate_base_url: str = Field(default="https://v6.exchangerate-api.com/v6", alias="EXCHANGE_RATE_BASE_URL")

    # --- Weather (bonus feature) -------------------------------------------
    openweather_api_key: str = Field(default="", alias="OPENWEATHER_API_KEY")

    # --- Web Search (bonus feature) -----------------------------------------
    serper_api_key: str = Field(default="", alias="SERPER_API_KEY")
    serper_base_url: str = Field(default="https://google.serper.dev", alias="SERPER_BASE_URL")

    # --- Caching -------------------------------------------------------
    cache_ttl_seconds: int = Field(default=300, alias="CACHE_TTL_SECONDS")
    cache_max_entries: int = Field(default=256, alias="CACHE_MAX_ENTRIES")

    # --- Networking / Retry Policy ---------------------------------------
    http_max_retries: int = Field(default=3, alias="HTTP_MAX_RETRIES")
    http_backoff_seconds: float = Field(default=1.5, alias="HTTP_BACKOFF_SECONDS")
    http_timeout_seconds: int = Field(default=15, alias="HTTP_TIMEOUT_SECONDS")

    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        """Whether the app is running in a production environment."""
        return self.app_env == "production"

    @computed_field  # type: ignore[misc]
    @property
    def has_flight_provider_credentials(self) -> bool:
        """Whether the active flight provider has usable credentials.

        Used by the UI's API Status indicator to warn the user before a
        tool call fails, rather than surfacing a raw exception mid-chat.
        """
        provider = self.flight_data_provider
        if provider is FlightDataProvider.AMADEUS:
            return bool(self.amadeus_api_key and self.amadeus_api_secret)
        if provider is FlightDataProvider.KIWI:
            return bool(self.kiwi_tequila_api_key)
        if provider is FlightDataProvider.AVIATIONSTACK:
            return bool(self.aviationstack_api_key)
        return False

    @computed_field  # type: ignore[misc]
    @property
    def has_geoapify_credentials(self) -> bool:
        """Whether the Airport Search Tool (Geoapify) has a usable key."""
        return bool(self.geoapify_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` singleton.

    Cached with :func:`functools.lru_cache` so environment parsing and
    validation happen exactly once per process, while every caller across
    the codebase (agent nodes, tools, UI components) shares one consistent
    configuration snapshot.
    """
    return Settings()
