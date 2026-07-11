"""Redis cache with in-memory fallback.

In development (no Redis URL configured) the cache silently falls back to
a plain dict — no external dependency required.

In production, set REDIS_URL in the environment (e.g. ``redis://localhost:6379/0``).

Usage::

    cache = get_cache()
    await cache.set("embeddings:sha256:abc", value, ttl=3600)
    hit = await cache.get("embeddings:sha256:abc")
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any

from app.core.logging import get_logger

_log = get_logger()


# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------

class _MemoryCacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: int | None) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl if ttl else None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.monotonic() > self.expires_at


class InMemoryCache:
    """Simple dict-backed async cache with TTL support."""

    def __init__(self) -> None:
        self._store: dict[str, _MemoryCacheEntry] = {}

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._store[key]
            return None
        return entry.value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        self._store[key] = _MemoryCacheEntry(value, ttl)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Redis-backed cache
# ---------------------------------------------------------------------------

class RedisCache:
    """Async Redis cache using aioredis (or redis[asyncio] ≥ 4.2)."""

    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis  # type: ignore[import]

        self._client = aioredis.from_url(url, decode_responses=False)

    async def get(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        encoded = json.dumps(value)
        if ttl:
            await self._client.setex(key, ttl, encoded)
        else:
            await self._client.set(key, encoded)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def clear(self) -> None:
        await self._client.flushdb()

    async def close(self) -> None:
        await self._client.aclose()


# ---------------------------------------------------------------------------
# Factory & singleton
# ---------------------------------------------------------------------------

_cache: InMemoryCache | RedisCache | None = None
_cache_lock = asyncio.Lock()


async def get_cache() -> InMemoryCache | RedisCache:
    """Return the process-level cache singleton.

    Tries Redis first (if REDIS_URL is set), falls back to in-memory.
    """
    global _cache
    if _cache is not None:
        return _cache

    async with _cache_lock:
        if _cache is not None:
            return _cache

        try:
            from app.core.config import get_settings
            settings = get_settings()
            redis_url = getattr(settings, "redis_url", None)
        except Exception:
            redis_url = None

        if redis_url:
            try:
                _cache = RedisCache(redis_url)
                # Ping to verify connectivity
                await _cache._client.ping()  # type: ignore[attr-defined]
                _log.info("cache_backend", backend="redis", url=redis_url)
            except Exception as exc:
                _log.warning("redis_unavailable_fallback", error=str(exc))
                _cache = InMemoryCache()
        else:
            _cache = InMemoryCache()
            _log.info("cache_backend", backend="memory")

        return _cache


def make_cache_key(*parts: str) -> str:
    """Build a deterministic cache key from multiple string parts."""
    combined = ":".join(parts)
    digest = hashlib.sha256(combined.encode()).hexdigest()[:16]
    return f"optiagent:{digest}"


def reset_cache() -> None:
    """Reset the cache singleton — test isolation only."""
    global _cache
    _cache = None
