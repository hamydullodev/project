from urllib.parse import urljoin

from app.tools.scrapers.base import fetch_html, normalize_product, parse_price

STORE_NAME = "PharmaClick"
BASE_URL = "https://pharmaclick.uz"
SEARCH_URL = "https://pharmaclick.uz/ru/catalog/"


def search(query: str, limit: int = 15) -> list[dict]:
    soup = fetch_html(SEARCH_URL, params={"q": query})
    if soup is None:
        return []

    items = soup.select("div.catalog_item_wrapp.item")
    products = []

    for item in items:
        title_el = item.select_one(".item-title a span")
        link_el = item.select_one(".item-title a")
        brand_el = item.select_one(".cml_man")
        price_el = item.select_one(".js_price_wrapper .values_wrapper")
        stock_el = item.select_one(".item-stock .value")

        if not title_el or not link_el:
            continue

        name = title_el.get_text(strip=True)
        price = parse_price(price_el.get_text(strip=True)) if price_el else None
        stock_text = stock_el.get_text(strip=True).lower() if stock_el else ""
        in_stock = "наличии" in stock_text or "mavjud" in stock_text

        products.append(
            normalize_product(
                store=STORE_NAME,
                name=name,
                price=price,
                url=urljoin(BASE_URL, link_el.get("href", "")),
                brand=brand_el.get_text(strip=True) if brand_el else None,
                in_stock=in_stock,
            )
        )
        if len(products) >= limit:
            break

    return products
