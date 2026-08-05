"""TTL caching layer for API responses (flight search, currency rates).

A thin wrapper over :class:`cachetools.TTLCache` keyed by a stable hash of
the call arguments, exposed as a decorator so tools/API clients can cache a
function without duplicating cache-key logic at every call site.
"""

from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Callable
from typing import Any, TypeVar

from cachetools import TTLCache

from app.config import get_settings

T = TypeVar("T")

_caches: dict[str, TTLCache] = {}


def _cache_for(namespace: str) -> TTLCache:
    if namespace not in _caches:
        settings = get_settings()
        _caches[namespace] = TTLCache(maxsize=settings.cache_max_entries, ttl=settings.cache_ttl_seconds)
    return _caches[namespace]


def _make_key(args: tuple, kwargs: dict) -> str:
    payload = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cached(namespace: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Cache a function's return value under ``namespace`` for the TTL window.

    Args:
        namespace: Logical cache name (e.g. ``"flight_search"``), so
            different tools don't collide on the same key space.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            cache = _cache_for(namespace)
            key = _make_key(args, kwargs)
            if key in cache:
                return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            return result

        return wrapper

    return decorator


def clear_cache(namespace: str | None = None) -> None:
    """Clear one cache namespace, or all of them when ``namespace`` is None."""
    if namespace is None:
        for cache in _caches.values():
            cache.clear()
        return
    _caches.get(namespace, TTLCache(maxsize=1, ttl=1)).clear()
