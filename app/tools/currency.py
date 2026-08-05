"""Currency Tool: real exchange-rate conversion (USD/EUR/UZS/...).

Bonus feature from the PDF spec ("Narxlarni so'mda ko'rsat"). Converts
either a single amount or every price in the most recent flight search
result, using live rates from :mod:`app.api.exchange_rate`.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.agent.memory import get_last_flights
from app.api.exceptions import ProviderError
from app.api.exchange_rate import get_exchange_rate_client
from app.utils.cache import cached
from app.utils.formatter import format_price
from app.utils.logger import get_logger
from app.utils.validators import InvalidInputError, validate_currency_code

logger = get_logger(__name__)


@cached("exchange_rate")
def _get_rate(base: str, target: str) -> float:
    return get_exchange_rate_client().get_rate(base, target).rate


@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount from one currency to another using a live rate.

    Args:
        amount: The amount to convert.
        from_currency: 3-letter source currency code, e.g. "USD".
        to_currency: 3-letter target currency code, e.g. "UZS".
    """
    try:
        base = validate_currency_code(from_currency)
        target = validate_currency_code(to_currency)
        rate = _get_rate(base, target)
    except (InvalidInputError, ProviderError) as exc:
        logger.warning("convert_currency failed: {}", exc)
        return f"⚠️ {exc}"

    converted = amount * rate
    return f"{format_price(amount, base)} = {format_price(converted, target)} (kurs: 1 {base} = {rate:.4f} {target})"


@tool
def convert_last_flight_prices(to_currency: str) -> str:
    """Convert every price from the most recent flight search into another currency.

    Args:
        to_currency: 3-letter target currency code, e.g. "UZS".
    """
    flights = [f for f in get_last_flights() if f.has_price]
    if not flights:
        return "⚠️ Konvertatsiya qilish uchun narxi mavjud reys topilmadi (aktiv provayder narx bermaydi)."

    try:
        target = validate_currency_code(to_currency)
    except InvalidInputError as exc:
        return f"⚠️ {exc}"

    lines = []
    for flight in flights:
        try:
            rate = _get_rate(flight.currency, target)
        except ProviderError as exc:
            logger.warning("convert_last_flight_prices failed: {}", exc)
            return f"⚠️ {exc}"
        converted = flight.price * rate
        lines.append(
            f"- {flight.airline} {flight.flight_number}: "
            f"{format_price(flight.price, flight.currency)} -> {format_price(converted, target)}"
        )
    return "\n".join(lines)
