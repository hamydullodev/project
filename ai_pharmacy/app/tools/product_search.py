from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.tools import tool

from app.database.db import cache_products, get_cached_products
from app.tools.scrapers import europharm, oxymed, pharmaclick

SCRAPERS = [oxymed, pharmaclick, europharm]


def _run_scrapers(query: str, limit_per_store: int) -> list[dict]:
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=len(SCRAPERS)) as executor:
        futures = {executor.submit(scraper.search, query, limit_per_store): scraper.STORE_NAME for scraper in SCRAPERS}
        for future in as_completed(futures):
            try:
                results.extend(future.result())
            except Exception:
                continue
    return results


def search_products(query: str, limit_per_store: int = 10, use_cache: bool = True) -> list[dict]:
    """Search for a product across all connected Uzbekistan online pharmacies."""
    normalized_query = query.strip().lower()

    if use_cache:
        cached = get_cached_products(normalized_query)
        if cached:
            return cached

    results = _run_scrapers(query, limit_per_store)
    if results:
        cache_products(normalized_query, results)
    return results


@tool
def search_products_tool(query: str) -> list[dict]:
    """Search for medicines/vitamins by name or brand across at least 3 Uzbekistan
    online pharmacies (OXYmed, PharmaClick, Europharm). Returns a list of products,
    each with: name, brand, price, currency, store, url, in_stock, dosage, package_size.
    Always use this tool to look up products — never invent product names or prices.
    """
    return search_products(query)
