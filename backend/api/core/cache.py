import json
import logging
from typing import Any, Optional
import redis
from api.core.config import settings

logger = logging.getLogger("sqlarena.cache")

# Shared Redis client connection pool
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=2,
)


class CacheService:
    """
    Cache-Aside abstraction over ElastiCache (Redis).
    Handles key retrieval, population with TTL, and key invalidation.
    """

    @staticmethod
    def get(key: str) -> Optional[Any]:
        try:
            val = redis_client.get(key)
            if val:
                logger.info("[Cache HIT] Key: %s", key)
                return json.loads(val)
        except Exception as e:
            logger.warning("[Cache Warning] Error reading from Redis: %s", e)
        return None

    @staticmethod
    def set(key: str, value: Any, ttl_seconds: int = settings.REDIS_CACHE_TTL_SECONDS) -> None:
        try:
            redis_client.set(key, json.dumps(value), ex=ttl_seconds)
            logger.info("[Cache SET] Key: %s (TTL: %ds)", key, ttl_seconds)
        except Exception as e:
            logger.warning("[Cache Warning] Error writing to Redis: %s", e)

    @staticmethod
    def invalidate(*keys: str) -> None:
        try:
            if keys:
                redis_client.delete(*keys)
                logger.info("[Cache INVALIDATE] Keys: %s", keys)
        except Exception as e:
            logger.warning("[Cache Warning] Error invalidating Redis keys: %s", e)
