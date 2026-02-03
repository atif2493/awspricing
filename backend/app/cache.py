# cache.py - v1.0
# TTL cache for pricing responses. Keys: service, region, currency, storage_class (if S3).
# Dependencies: none. Port: N/A.

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class TTLCache:
    """Simple in-memory TTL cache. Default TTL 24 hours."""

    def __init__(self, ttl_seconds: float = 86400):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}

    def _key(self, **kwargs: Any) -> str:
        parts = [f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None]
        return "|".join(parts)

    def get(self, **kwargs: Any) -> tuple[Any, float] | None:
        """Return (value, cached_at_timestamp) or None if miss/expired."""
        k = self._key(**kwargs)
        if k not in self._store:
            return None
        val, cached_at = self._store[k]
        if time.monotonic() - cached_at > self._ttl:
            del self._store[k]
            return None
        return (val, cached_at)

    def set(self, value: Any, **kwargs: Any) -> None:
        k = self._key(**kwargs)
        self._store[k] = (value, time.monotonic())

    def invalidate(self, **kwargs: Any) -> bool:
        """Remove entry if present. Returns True if removed."""
        k = self._key(**kwargs)
        if k in self._store:
            del self._store[k]
            return True
        return False

    def invalidate_all(self) -> None:
        self._store.clear()


def cached(cache: TTLCache, key_fields: list[str]):
    """Decorator: cache result of async or sync function by key_fields (kwargs names)."""

    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            key_kw = {k: kwargs.get(k) for k in key_fields if k in kwargs}
            hit = cache.get(**key_kw)
            if hit is not None:
                return hit[0]
            result = f(*args, **kwargs)
            cache.set(result, **key_kw)
            return result
        return wrapper
    return decorator
