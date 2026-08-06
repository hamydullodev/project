"""Backend HTTP client + shared product formatting/ranking helpers.

Kept separate from the components so both the chat panel and the
result/compare pages can reuse the same product parsing and badge logic
without duplicating it.
"""

from __future__ import annotations

import json

import requests

from app.config import API_HOST, API_PORT

API_URL = f"http://{'localhost' if API_HOST == '0.0.0.0' else API_HOST}:{API_PORT}"


def call_agent(thread_id: str, message: str) -> dict:
    try:
        resp = requests.post(
            f"{API_URL}/chat",
            json={"message": message, "thread_id": thread_id},
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {
            "answer": f"Xatolik: backend bilan bog'lanib bo'lmadi ({e}).",
            "tool_calls": [],
            "tool_results": [],
        }


def extract_products(tool_results: list[dict]) -> list[dict]:
    rows = []
    for tr in tool_results:
        content = tr.get("result")
        try:
            data = json.loads(content) if isinstance(content, str) else content
        except (TypeError, ValueError):
            continue

        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict) and "comparison_table" in data:
            candidates = data["comparison_table"]
        elif isinstance(data, dict) and "name" in data:
            candidates = [data]
        else:
            candidates = []

        for p in candidates:
            if isinstance(p, dict) and "name" in p:
                rows.append(p)
    return rows


def format_price(price, currency="UZS") -> str:
    if price is None:
        return "Narxi noma'lum"
    return f"{price:,.0f}".replace(",", " ") + f" {currency}"


def product_id(product: dict) -> str:
    return f"{product.get('name')}|{product.get('store')}|{product.get('price')}"


def _unit_price(product: dict) -> float | None:
    try:
        size = float(str(product.get("package_size")).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if size <= 0 or product.get("price") is None:
        return None
    return product["price"] / size


def compute_badges(products: list[dict]) -> tuple[str | None, str | None]:
    """Return (cheapest_id, best_value_id). Best value = lowest price-per-unit
    among in-stock items (falls back to None if no product has a parseable
    package size)."""
    priced = [p for p in products if p.get("price") is not None]
    if not priced:
        return None, None
    cheapest_id = product_id(min(priced, key=lambda p: p["price"]))

    value_candidates = [(product_id(p), _unit_price(p)) for p in priced if p.get("in_stock", True)]
    value_candidates = [(pid, up) for pid, up in value_candidates if up is not None]
    best_value_id = min(value_candidates, key=lambda x: x[1])[0] if value_candidates else None
    return cheapest_id, best_value_id


def market_summary(query: str, results: list[dict]) -> str | None:
    """One-line natural-language summary highlighting cheapest price and savings."""
    priced = [p for p in results if p.get("price") is not None]
    if not priced:
        return None
    cheapest = min(priced, key=lambda p: p["price"])
    avg_price = sum(p["price"] for p in priced) / len(priced)
    savings = (avg_price - cheapest["price"]) / avg_price * 100 if avg_price else 0
    text = (
        f'"{query}" bo\'yicha **{len(results)} ta** mos mahsulot topildi. '
        f"Eng arzon variant — **{format_price(cheapest['price'], cheapest.get('currency', 'UZS'))}** "
        f"({cheapest.get('store')}). O'rtacha bozor narxi — **{format_price(avg_price)}**."
    )
    if savings > 1:
        text += f" Eng arzon variantni tanlab, o'rtachaga nisbatan **~{savings:.0f}%** tejashingiz mumkin."
    return text
