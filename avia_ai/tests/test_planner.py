from datetime import date

from app.agent.planner import resolve_relative_dates


def test_resolves_bugun_to_today():
    today = date(2026, 8, 5)
    result = resolve_relative_dates("bugun uchadigan reyslar", today=today)
    assert "2026-08-05" in result


def test_resolves_ertaga_to_tomorrow():
    today = date(2026, 8, 5)
    result = resolve_relative_dates("ertaga uchadigan reyslar", today=today)
    assert "2026-08-06" in result


def test_leaves_absolute_dates_untouched():
    today = date(2026, 8, 5)
    result = resolve_relative_dates("15-avgust kuni uchadigan reyslar", today=today)
    assert result == "15-avgust kuni uchadigan reyslar"
