"""Cache abstraction with Redis backend and in-memory fallback."""
from __future__ import annotations

import json
import time
from typing import Any

from .config import get_settings


class MemoryCache:
    """Very small TTL cache used when Redis is not configured."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._counters: dict[str, tuple[float, int]] = {}

    async def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if not item:
            return None
        expires, value = item
        if expires < time.monotonic():
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (time.monotonic() + ttl, value)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def delete_prefix(self, prefix: str) -> None:
        for key in [k for k in self._store if k.startswith(prefix)]:
            self._store.pop(key, None)

    async def hit(self, key: str, window: int) -> int:
        now = time.monotonic()
        expires, count = self._counters.get(key, (now + window, 0))
        if expires < now:
            expires, count = now + window, 0
        count += 1
        self._counters[key] = (expires, count)
        return count

    async def reset(self, key: str) -> None:
        self._counters.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()
        self._counters.clear()


class RedisCache:
    def __init__(self, client) -> None:
        self._client = client

    async def get(self, key: str) -> Any | None:
        value = await self._client.get(key)
        return json.loads(value) if value is not None else None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        await self._client.set(key, json.dumps(value), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def delete_prefix(self, prefix: str) -> None:
        async for key in self._client.scan_iter(match=f"{prefix}*"):
            await self._client.delete(key)

    async def hit(self, key: str, window: int) -> int:
        pipeline = self._client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, window, nx=True)
        count, _ = await pipeline.execute()
        return int(count)

    async def reset(self, key: str) -> None:
        await self._client.delete(key)

    async def clear(self) -> None:
        await self._client.flushdb()


_cache: MemoryCache | RedisCache | None = None


def get_cache() -> MemoryCache | RedisCache:
    global _cache
    if _cache is None:
        settings = get_settings()
        if settings.redis_url:
            from redis.asyncio import from_url

            client = from_url(settings.redis_url, decode_responses=True)
            _cache = RedisCache(client)
        else:
            _cache = MemoryCache()
    return _cache


async def invalidate_catalog_cache() -> None:
    """Drop cached stats and counts after any catalog mutation."""
    cache = get_cache()
    await cache.delete("stats:summary")
    await cache.delete_prefix("count:")
