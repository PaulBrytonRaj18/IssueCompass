import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
    return _redis


async def cache_get(key: str) -> Optional[Any]:
    try:
        r = await get_redis()
        data = await r.get(key)
        if data is None:
            return None
        return json.loads(data)
    except Exception as e:
        logger.warning("Cache GET error for key %s: %s", key, e)
        return None


async def cache_set(key: str, value: Any, ttl: int = 3600):
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value))
    except Exception as e:
        logger.warning("Cache SET error for key %s: %s", key, e)


async def cache_delete_pattern(pattern: str):
    try:
        r = await get_redis()
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await r.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        logger.warning("Cache DELETE pattern error for %s: %s", pattern, e)


async def cache_ping() -> bool:
    try:
        r = await get_redis()
        return await r.ping()
    except Exception:
        return False
