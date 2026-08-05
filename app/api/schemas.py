"""Pydantic schemas for flights, airports, currency, and weather data.

These are the only shapes that cross the boundary between ``app.api``
(network I/O) and the rest of the codebase (tools, agent, UI). Every field
here traces back to a real API response — nothing is synthesized by the LLM.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Flight(BaseModel):
    """A single flight offer, normalized across providers.

    ``price``/``currency`` are optional: schedule-only providers (e.g.
    AviationStack's free tier) don't expose fares at all. Rather than
    inventing a number, those fields stay ``None`` and the formatter shows
    "narx mavjud emas" instead of a fabricated price.
    """

    airline: str
    airline_code: str = ""
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    stops: int
    cabin_class: str = "ECONOMY"
    price: float | None = None
    currency: str = ""
    booking_link: str = ""
    status: str = ""

    @property
    def duration_label(self) -> str:
        hours, minutes = divmod(self.duration_minutes, 60)
        return f"{hours}h {minutes}m"

    @property
    def stops_label(self) -> str:
        if self.stops == 0:
            return "To'g'ridan-to'g'ri"
        return f"{self.stops} to'xtash"

    @property
    def has_price(self) -> bool:
        return self.price is not None


class FlightSearchQuery(BaseModel):
    """Normalized parameters for a flight search, produced by the planner."""

    origin: str
    destination: str
    departure_date: str
    return_date: str | None = None
    adults: int = 1
    children: int = 0
    cabin_class: str | None = None
    max_stops: int | None = None
    airline: str | None = None
    time_of_day: str | None = None  # morning | afternoon | evening | night
    sort_by: str | None = None  # price | duration | departure_time


class Airport(BaseModel):
    """An airport resolved via the Airport Search Tool (Geoapify)."""

    iata_code: str = ""
    name: str
    city: str = ""
    country: str = ""
    latitude: float | None = None
    longitude: float | None = None


class CurrencyRate(BaseModel):
    """A single from->to conversion rate at the time of lookup."""

    base_currency: str
    target_currency: str
    rate: float
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class WeatherInfo(BaseModel):
    """Destination weather snapshot (bonus feature)."""

    city: str
    temperature_celsius: float
    condition: str
    humidity_percent: int | None = None


class WebSearchResult(BaseModel):
    """A single organic result from the Web Search Tool (bonus feature)."""

    title: str
    link: str
    snippet: str = ""
