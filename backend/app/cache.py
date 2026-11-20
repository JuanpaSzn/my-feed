"""Caché ligera: Redis si está configurado, si no un diccionario en memoria con TTL.

Se usa para las sesiones de feed (lista de IDs ya calculada), bloqueos del
planificador y respuestas costosas. Si Redis se cae, la app sigue funcionando.
"""
import json
import logging
import time
from typing import Any

from .config import get_settings

log = logging.getLogger("myfeed.cache")


class MemoryCache:
    def __init__(self, max_items: int = 2000):
        self._data: dict[str, tuple[float, str]] = {}
        self._max = max_items

    async def get(self, key: str) -> str | None:
        hit = self._data.get(key)
        if not hit:
            return None
        exp, val = hit
        if exp and exp < time.monotonic():
            self._data.pop(key, None)
            return None
        return val

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        if len(self._data) >= self._max:
            # Expulsa la mitad más antigua: suficiente para una app personal.
            for k in list(self._data)[: self._max // 2]:
                self._data.pop(k, None)
        self._data[key] = (time.monotonic() + ttl if ttl else 0, value)

    async def delete(self, *keys: str) -> None:
        for k in keys:
            self._data.pop(k, None)

    async def set_nx(self, key: str, value: str, ttl: int) -> bool:
        if await self.get(key) is not None:
            return False
        await self.set(key, value, ttl)
        return True

    async def delete_prefix(self, prefix: str) -> None:
        for k in [k for k in self._data if k.startswith(prefix)]:
            self._data.pop(k, None)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None


class RedisCache:
    def __init__(self, url: str):
        import redis.asyncio as redis

        self._r = redis.from_url(url, decode_responses=True, socket_timeout=3, socket_connect_timeout=3)
        self._fallback = MemoryCache()
        self._down_until = 0.0

    async def _call(self, name: str, *args, **kwargs):
        if self._down_until > time.monotonic():
            return await getattr(self._fallback, name)(*args, **kwargs)
        try:
            if name == "get":
                return await self._r.get(args[0])
            if name == "set":
                key, value = args[0], args[1]
                ttl = kwargs.get("ttl") or (args[2] if len(args) > 2 else None)
                return await self._r.set(key, value, ex=ttl)
            if name == "delete":
                return await self._r.delete(*args) if args else None
            if name == "set_nx":
                return bool(await self._r.set(args[0], args[1], ex=args[2], nx=True))
            if name == "delete_prefix":
                keys = [k async for k in self._r.scan_iter(match=f"{args[0]}*", count=200)]
                if keys:
                    await self._r.delete(*keys)
                return None
            if name == "ping":
                return bool(await self._r.ping())
        except Exception as exc:  # Redis caído: degradar a memoria 30 s
            log.warning("Redis no disponible (%s); uso caché en memoria", exc)
            self._down_until = time.monotonic() + 30
            return await getattr(self._fallback, name)(*args, **kwargs)

    async def get(self, key):
        return await self._call("get", key)

    async def set(self, key, value, ttl=None):
        return await self._call("set", key, value, ttl=ttl)

    async def delete(self, *keys):
        return await self._call("delete", *keys)

    async def set_nx(self, key, value, ttl):
        return await self._call("set_nx", key, value, ttl)

    async def delete_prefix(self, prefix):
        return await self._call("delete_prefix", prefix)

    async def ping(self):
        return await self._call("ping")

    async def close(self):
        try:
            await self._r.aclose()
        except Exception:
            pass


_cache: MemoryCache | RedisCache | None = None


def get_cache() -> MemoryCache | RedisCache:
    global _cache
    if _cache is None:
        url = get_settings().redis_url
        _cache = RedisCache(url) if url else MemoryCache()
    return _cache


async def get_json(key: str) -> Any:
    raw = await get_cache().get(key)
    return json.loads(raw) if raw else None


async def set_json(key: str, value: Any, ttl: int | None = None) -> None:
    await get_cache().set(key, json.dumps(value, default=str), ttl=ttl)
