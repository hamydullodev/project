import re

import requests
from bs4 import BeautifulSoup

from app.config import REQUEST_TIMEOUT, USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}


def fetch_html(url: str, params: dict | None = None) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    return BeautifulSoup(resp.text, "lxml")


def parse_price(text: str) -> float | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return float(digits) if digits else None


def normalize_product(
    store: str,
    name: str,
    price: float | None,
    url: str,
    brand: str | None = None,
    product_type: str | None = None,
    dosage: str | None = None,
    package_size: str | None = None,
    currency: str = "UZS",
    in_stock: bool = True,
) -> dict:
    dosage_match = re.search(r"(\d+[.,]?\d*\s?(?:mg|mcg|mkg|iu|iu|мг|мкг|ме|g|г))", name, re.I)
    package_match = re.search(r"№\s?(\d+)|(\d+)\s?(?:tab|caps|kaps|шт|таб|капс)", name, re.I)
    return {
        "store": store,
        "name": name.strip(),
        "brand": brand.strip() if brand else None,
        "product_type": product_type,
        "dosage": dosage or (dosage_match.group(1) if dosage_match else None),
        "package_size": package_size or (package_match.group(1) or package_match.group(2) if package_match else None),
        "price": price,
        "currency": currency,
        "url": url,
        "in_stock": in_stock,
    }
