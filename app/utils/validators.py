"""Input validation helpers (IATA codes, dates, currency codes, etc.).

Tools call these before hitting an external API so malformed LLM-supplied
arguments turn into a clear ``InvalidInputError`` instead of a confusing
provider-side 400 response.
"""

from __future__ import annotations

import re
from datetime import date, datetime

_IATA_RE = re.compile(r"^[A-Za-z]{3}$")
_CURRENCY_RE = re.compile(r"^[A-Za-z]{3}$")


class InvalidInputError(ValueError):
    """Raised when a user/LLM-supplied argument fails validation."""


def validate_iata_code(code: str) -> str:
    """Normalize and validate a 3-letter IATA airport code."""
    if not code or not _IATA_RE.match(code.strip()):
        raise InvalidInputError(f"'{code}' haqiqiy IATA kodi emas. 3 harfli kod kerak (masalan, TAS).")
    return code.strip().upper()


def validate_date(value: str, *, field_name: str = "sana") -> str:
    """Validate an ISO ``YYYY-MM-DD`` date string and ensure it's not in the past."""
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError) as exc:
        raise InvalidInputError(
            f"{field_name.capitalize()} formati noto'g'ri: '{value}'. "
            "YYYY-MM-DD formatida kiriting (masalan, 2026-08-15)."
        ) from exc

    if parsed < date.today():
        raise InvalidInputError(f"{field_name.capitalize()} o'tmishda: '{value}'. Kelajakdagi sanani kiriting.")
    return parsed.isoformat()


def validate_currency_code(code: str) -> str:
    """Normalize and validate a 3-letter ISO currency code."""
    if not code or not _CURRENCY_RE.match(code.strip()):
        raise InvalidInputError(f"'{code}' haqiqiy valyuta kodi emas. 3 harfli kod kerak (masalan, USD, UZS).")
    return code.strip().upper()


def validate_passenger_count(adults: int, children: int = 0) -> tuple[int, int]:
    """Ensure passenger counts are within a sane, provider-accepted range."""
    if adults < 1:
        raise InvalidInputError("Kamida 1 ta kattalar yo'lovchisi bo'lishi kerak.")
    if adults + children > 9:
        raise InvalidInputError("Jami yo'lovchilar soni 9 tadan oshmasligi kerak.")
    if children < 0:
        raise InvalidInputError("Bolalar soni manfiy bo'lishi mumkin emas.")
    return adults, children
