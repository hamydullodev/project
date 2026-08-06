from app.tools.scrapers.base import fetch_html, normalize_product, parse_price

STORE_NAME = "OXYmed"
SEARCH_URL = "https://oxymed.uz/catalog/search"


def search(query: str, limit: int = 15) -> list[dict]:
    soup = fetch_html(SEARCH_URL, params={"q": query})
    if soup is None:
        return []

    divs = soup.select("div.product-item")
    links = soup.select("a.product-item__link")
    products = []

    for div, link in zip(divs, links):
        name_el = div.select_one(".product-item__name")
        price_el = div.select_one(".product-item__price")
        avail_el = div.select_one(".product-item__avail")

        if not name_el:
            continue

        name = name_el.get_text(strip=True)
        price = None
        if price_el:
            direct_text = "".join(t for t in price_el.find_all(string=True, recursive=False))
            price = parse_price(direct_text)
        avail_text = avail_el.get_text(strip=True).lower() if avail_el else ""
        in_stock = "наличии" in avail_text or "mavjud" in avail_text

        products.append(
            normalize_product(
                store=STORE_NAME,
                name=name,
                price=price,
                url=link.get("href", ""),
                in_stock=in_stock,
            )
        )
        if len(products) >= limit:
            break

    return products
