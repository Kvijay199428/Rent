"""
Propaura Cache Service — Redis-backed with fail-open design.

If Redis is unavailable, all operations silently fall through.
Caching can never break the app.
"""
import os
import json
import hashlib
import functools
import logging
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)

_redis = None
_prefix = "propaura:"


def _get_redis():
    """Lazy-init Redis connection. Returns None if unavailable."""
    global _redis
    if _redis is not None:
        return _redis
    url = os.environ.get("REDIS_URL")
    if not url:
        return None
    try:
        import redis as _r
        _redis = _r.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        _redis.ping()
        logger.info("Redis connected: %s", url)
        return _redis
    except Exception as e:
        logger.warning("Redis unavailable (fail-open): %s", e)
        _redis = None
        return None


def cache_get(key: str) -> Optional[Any]:
    r = _get_redis()
    if not r:
        return None
    try:
        val = r.get(_prefix + key)
        return json.loads(val) if val else None
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl: int = 30) -> None:
    r = _get_redis()
    if not r:
        return
    try:
        r.setex(_prefix + key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_delete(key: str) -> None:
    r = _get_redis()
    if not r:
        return
    try:
        r.delete(_prefix + key)
    except Exception:
        pass


def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching pattern. Uses SCAN for safety."""
    r = _get_redis()
    if not r:
        return
    try:
        cursor = 0
        full = _prefix + pattern
        while True:
            cursor, keys = r.scan(cursor, match=full, count=100)
            if keys:
                r.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass


def cache_stats() -> dict:
    """Return Redis connection status and key count for health checks."""
    r = _get_redis()
    if not r:
        return {"connected": False, "provider": "in-memory"}
    try:
        info = r.info("keyspace")
        db_keys = 0
        for db, db_info in info.items():
            if db.startswith("db"):
                db_keys += db_info.get("keys", 0)
        ping = r.ping()
        return {"connected": bool(ping), "provider": "redis", "key_count": db_keys}
    except Exception:
        return {"connected": False, "provider": "redis", "key_count": 0}


def cached(prefix: str, ttl: int = 30, key_fn: Optional[Callable] = None):
    """Decorator: cache function result in Redis.

    key_fn: optional callable(*args, **kwargs) -> str for custom cache keys.
    If not provided, uses hashlib of args+kwargs.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if key_fn:
                cache_key = f"{prefix}:{key_fn(*args, **kwargs)}"
            else:
                raw = json.dumps(
                    {"a": str(args), "k": str(kwargs)}, default=str
                )
                cache_key = f"{prefix}:{hashlib.md5(raw.encode()).hexdigest()}"

            result = cache_get(cache_key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            if result is not None:
                cache_set(cache_key, result, ttl)
            return result

        wrapper.invalidate = lambda: cache_delete_pattern(f"{prefix}:*")
        return wrapper

    return decorator
