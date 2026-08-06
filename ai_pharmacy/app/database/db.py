import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from app.config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS product_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    store TEXT NOT NULL,
    name TEXT NOT NULL,
    brand TEXT,
    product_type TEXT,
    dosage TEXT,
    package_size TEXT,
    price REAL,
    currency TEXT,
    url TEXT,
    in_stock INTEGER,
    fetched_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_product_cache_query ON product_cache(query);

CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    result_count INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    store TEXT NOT NULL,
    price REAL,
    currency TEXT,
    url TEXT,
    added_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS price_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    target_price REAL NOT NULL,
    created_at INTEGER NOT NULL,
    triggered INTEGER DEFAULT 0
);
"""

CACHE_TTL_SECONDS = 15 * 60


@contextmanager
def get_connection():
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def cache_products(query: str, products: list[dict]):
    now = int(time.time())
    with get_connection() as conn:
        conn.execute("DELETE FROM product_cache WHERE query = ?", (query,))
        conn.executemany(
            """
            INSERT INTO product_cache
                (query, store, name, brand, product_type, dosage, package_size,
                 price, currency, url, in_stock, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    query,
                    p.get("store"),
                    p.get("name"),
                    p.get("brand"),
                    p.get("product_type"),
                    p.get("dosage"),
                    p.get("package_size"),
                    p.get("price"),
                    p.get("currency", "UZS"),
                    p.get("url"),
                    1 if p.get("in_stock") else 0,
                    now,
                )
                for p in products
            ],
        )
        conn.execute(
            "INSERT INTO search_history (query, result_count, created_at) VALUES (?, ?, ?)",
            (query, len(products), now),
        )


def get_cached_products(query: str, max_age: int = CACHE_TTL_SECONDS) -> list[dict] | None:
    cutoff = int(time.time()) - max_age
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM product_cache WHERE query = ? AND fetched_at >= ?",
            (query, cutoff),
        ).fetchall()
    if not rows:
        return None
    return [dict(r) for r in rows]


def get_recent_searches(limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT query, result_count, created_at FROM search_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_trending_searches(limit: int = 6) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT query, COUNT(*) AS search_count, MAX(created_at) AS last_searched "
            "FROM search_history WHERE result_count > 0 "
            "GROUP BY query ORDER BY search_count DESC, last_searched DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_favorite(product: dict):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO favorites (name, store, price, currency, url, added_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                product.get("name"),
                product.get("store"),
                product.get("price"),
                product.get("currency", "UZS"),
                product.get("url"),
                int(time.time()),
            ),
        )


def list_favorites() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM favorites ORDER BY added_at DESC").fetchall()
    return [dict(r) for r in rows]


def remove_favorite(favorite_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM favorites WHERE id = ?", (favorite_id,))


def add_price_alert(query: str, target_price: float):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO price_alerts (query, target_price, created_at) VALUES (?, ?, ?)",
            (query, target_price, int(time.time())),
        )


def list_price_alerts() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM price_alerts ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]
