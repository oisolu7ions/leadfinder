"""Redis connection helpers."""

from functools import lru_cache

import redis

from app.core.config import Settings, get_settings


@lru_cache
def get_redis_client(settings: Settings | None = None) -> redis.Redis:
    """Return a cached Redis client."""
    settings = settings or get_settings()
    return redis.from_url(str(settings.redis_url), decode_responses=True)


def ping_redis(client: redis.Redis | None = None) -> bool:
    """Return True if Redis responds to PING."""
    client = client or get_redis_client()
    try:
        return bool(client.ping())
    except redis.RedisError:
        return False


def reset_redis_client() -> None:
    """Clear cached Redis client — used in tests."""
    get_redis_client.cache_clear()
