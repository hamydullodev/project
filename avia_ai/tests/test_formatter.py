from datetime import datetime

from app.api.schemas import Flight
from app.utils.formatter import (
    comparison_summary,
    flights_to_markdown_table,
    format_duration,
    format_price,
)


def _flight(**overrides) -> Flight:
    defaults = dict(
        airline="Turkish Airlines",
        airline_code="TK",
        flight_number="TK371",
        origin="TAS",
        destination="IST",
        departure_time=datetime(2026, 8, 15, 2, 30),
        arrival_time=datetime(2026, 8, 15, 5, 45),
        duration_minutes=195,
        stops=0,
        price=120.5,
        currency="USD",
    )
    defaults.update(overrides)
    return Flight(**defaults)


def test_format_price_with_amount():
    assert format_price(120.5, "USD") == "120.50 USD"


def test_format_price_with_none_is_explicit_not_zero():
    assert format_price(None, "USD") == "narx mavjud emas"


def test_format_duration():
    assert format_duration(195) == "3h 15m"


def test_flights_to_markdown_table_empty():
    assert "topilmadi" in flights_to_markdown_table([])


def test_flights_to_markdown_table_contains_flight_number():
    table = flights_to_markdown_table([_flight()])
    assert "TK371" in table


def test_comparison_summary_falls_back_when_no_prices():
    flights = [_flight(price=None, currency=""), _flight(flight_number="TK999", price=None, currency="")]
    summary = comparison_summary(flights)
    assert "taqdim etmaydi" in summary


def test_comparison_summary_picks_cheapest_when_priced():
    flights = [_flight(price=200), _flight(flight_number="TK999", price=100)]
    summary = comparison_summary(flights)
    assert "TK999" in summary
