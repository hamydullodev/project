from langchain_core.tools import tool

from app.tools.product_search import search_products


@tool
def filter_products_tool(
    query: str,
    max_price: float | None = None,
    min_price: float | None = None,
    brand: str | None = None,
    package_size: str | None = None,
    in_stock_only: bool = False,
) -> list[dict]:
    """Search for a product and filter the results by price range (max_price/min_price
    in UZS), brand name, package size (e.g. "120" for 120 capsules/tablets), and/or
    availability. Use this when the user gives constraints like "under 200000 so'm",
    "only Solgar", or "120 capsule packs".
    """
    products = search_products(query)

    if max_price is not None:
        products = [p for p in products if p.get("price") and p["price"] <= max_price]
    if min_price is not None:
        products = [p for p in products if p.get("price") and p["price"] >= min_price]
    if brand:
        products = [p for p in products if (p.get("brand") or "").lower() == brand.lower()]
    if package_size:
        products = [p for p in products if p.get("package_size") == str(package_size)]
    if in_stock_only:
        products = [p for p in products if p.get("in_stock")]

    products.sort(key=lambda p: (p.get("price") is None, p.get("price") or 0))
    return products
