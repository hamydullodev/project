from langchain_core.tools import tool

from app.tools.product_search import search_products


@tool
def compare_products_tool(query: str, brands: list[str] | None = None) -> dict:
    """Compare prices of a product (optionally restricted to specific brands, e.g.
    ["Solgar", "NOW Foods"]) across all connected Uzbekistan online pharmacies.
    Returns a comparison table (list of rows) sorted by price ascending, plus the
    cheapest and most expensive entries. Use this when the user wants to compare
    prices/brands/stores for the same or similar product.
    """
    products = search_products(query)

    if brands:
        brand_set = {b.lower() for b in brands}
        products = [p for p in products if (p.get("brand") or "").lower() in brand_set]

    priced = [p for p in products if p.get("price")]
    priced.sort(key=lambda p: p["price"])

    table = [
        {
            "name": p["name"],
            "brand": p.get("brand"),
            "dosage": p.get("dosage"),
            "package_size": p.get("package_size"),
            "price": p["price"],
            "currency": p.get("currency", "UZS"),
            "store": p["store"],
            "in_stock": bool(p.get("in_stock")),
            "url": p.get("url"),
        }
        for p in priced
    ]

    return {
        "query": query,
        "count": len(table),
        "comparison_table": table,
        "cheapest": table[0] if table else None,
        "most_expensive": table[-1] if table else None,
    }


@tool
def find_cheapest_tool(query: str) -> dict | None:
    """Find the single cheapest available (in-stock) product for a given
    medicine/vitamin name across all connected Uzbekistan online pharmacies.
    Use this when the user asks for "the cheapest X" or "best price for X".
    """
    products = search_products(query)
    in_stock_priced = [p for p in products if p.get("price") and p.get("in_stock")]
    if not in_stock_priced:
        return None
    cheapest = min(in_stock_priced, key=lambda p: p["price"])
    return {
        "name": cheapest["name"],
        "brand": cheapest.get("brand"),
        "price": cheapest["price"],
        "currency": cheapest.get("currency", "UZS"),
        "store": cheapest["store"],
        "url": cheapest.get("url"),
    }
