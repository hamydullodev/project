from app.api.aviationstack import AviationStackClient


def test_parse_leg_never_sets_a_fabricated_price():
    leg = {
        "flight_date": "2026-08-05",
        "flight_status": "scheduled",
        "departure": {"iata": "TAS", "scheduled": "2026-08-05T09:35:00+00:00"},
        "arrival": {"iata": "IST", "scheduled": "2026-08-05T12:55:00+00:00"},
        "airline": {"name": "Turkish Airlines", "iata": "TK"},
        "flight": {"number": "371", "iata": "TK371"},
    }

    flight = AviationStackClient._parse_leg(leg)

    assert flight.price is None
    assert flight.has_price is False
    assert flight.airline == "Turkish Airlines"
    assert flight.flight_number == "TK371"
    assert flight.duration_minutes == 200
    assert flight.status == "scheduled"


def test_is_usable_requires_both_scheduled_times():
    assert AviationStackClient._is_usable({"departure": {"scheduled": "x"}, "arrival": {"scheduled": "y"}})
    assert not AviationStackClient._is_usable({"departure": {}, "arrival": {"scheduled": "y"}})
