from __future__ import annotations

from functools import lru_cache

import redis.asyncio as redis

from app.core.config import get_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


async def set_json(key: str, payload: str, ttl_seconds: int = 3600) -> None:
    client = get_redis_client()
    try:
        await client.set(key, payload, ex=ttl_seconds)
    except Exception:
        return
