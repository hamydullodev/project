from datetime import date, timedelta

import pytest

from app.utils.validators import (
    InvalidInputError,
    validate_currency_code,
    validate_date,
    validate_iata_code,
    validate_passenger_count,
)


def test_validate_iata_code_normalizes_case():
    assert validate_iata_code("tas") == "TAS"


def test_validate_iata_code_rejects_wrong_length():
    with pytest.raises(InvalidInputError):
        validate_iata_code("TASH")


def test_validate_date_accepts_future_date():
    future = (date.today() + timedelta(days=10)).isoformat()
    assert validate_date(future) == future


def test_validate_date_rejects_past_date():
    past = (date.today() - timedelta(days=1)).isoformat()
    with pytest.raises(InvalidInputError):
        validate_date(past)


def test_validate_date_rejects_bad_format():
    with pytest.raises(InvalidInputError):
        validate_date("15-08-2026")


def test_validate_currency_code_normalizes_case():
    assert validate_currency_code("usd") == "USD"


def test_validate_passenger_count_requires_at_least_one_adult():
    with pytest.raises(InvalidInputError):
        validate_passenger_count(0, 0)


def test_validate_passenger_count_caps_total():
    with pytest.raises(InvalidInputError):
        validate_passenger_count(8, 5)


def test_validate_passenger_count_ok():
    assert validate_passenger_count(2, 1) == (2, 1)
