import re
from urllib.parse import urljoin

from app.tools.scrapers.base import fetch_html, normalize_product, parse_price

STORE_NAME = "Europharm"
BASE_URL = "https://europharm.uz"
CATEGORY_URL = "https://europharm.uz/витамины-и-бады"
MAX_PAGES = 4

# Europharm's SSR endpoint does not honor a server-side search query, so we
# page through the vitamins/supplements category and filter client-side.
LATIN_TO_CYRILLIC_HINTS = {
    "vitamin": "витамин",
    "d3": "д3",
    "magnesium": "магни",
    "omega": "омега",
    "calcium": "кальц",
}


def _tokenize(query: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", query.lower())
    expanded = set(tokens)
    for tok in tokens:
        if tok in LATIN_TO_CYRILLIC_HINTS:
            expanded.add(LATIN_TO_CYRILLIC_HINTS[tok])
    return list(expanded)


def _matches(name: str, tokens: list[str]) -> bool:
    name_lower = name.lower()
    return any(tok in name_lower for tok in tokens)


def search(query: str, limit: int = 15) -> list[dict]:
    tokens = _tokenize(query)
    products = []
    seen_urls = set()

    for page in range(1, MAX_PAGES + 1):
        soup = fetch_html(CATEGORY_URL, params={"page": page})
        if soup is None:
            break

        items = soup.select("div.product-item")
        if not items:
            break

        for item in items:
            name_el = item.select_one("h3[itemprop='name']")
            link_el = item.select_one("a[href]")
            if not name_el or not link_el:
                continue

            name = name_el.get_text(strip=True)
            if not _matches(name, tokens):
                continue

            url = urljoin(BASE_URL, link_el.get("href", ""))
            if url in seen_urls:
                continue
            seen_urls.add(url)

            brand_el = link_el.select_one("p")
            price_el = item.select_one("[itemprop='price']")
            avail_el = item.select_one("[itemprop='availability']")

            price_raw = price_el.get("content") if price_el else None
            price = parse_price(price_raw) if price_raw else None
            avail_content = (avail_el.get("content") or "") if avail_el else ""
            in_stock = "instock" in avail_content.lower() if avail_content else True

            products.append(
                normalize_product(
                    store=STORE_NAME,
                    name=name,
                    price=price,
                    url=url,
                    brand=brand_el.get_text(strip=True) if brand_el else None,
                    in_stock=in_stock,
                )
            )
            if len(products) >= limit:
                return products

    return products
