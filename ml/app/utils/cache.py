from __future__ import annotations

import json
import os
from typing import Any, Optional

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DEFAULT_TTL = int(os.getenv("CACHE_TTL_SECONDS", "1800"))

_redis_client: Optional[redis.Redis] = None


def _client() -> redis.Redis:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    _redis_client = redis.from_url(
        REDIS_URL,
        socket_timeout=0.4,      
        retry_on_timeout=True,
        health_check_interval=30,
        decode_responses=False,   
    )
    return _redis_client



def cache_get(key: str) -> Any | None:
    try:
        raw = _client().get(key)
        if raw is None:
            return None
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
    """
    Set key to JSON(value) with TTL. Uses DEFAULT_TTL if ttl_seconds is None.
    """
    try:
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        _client().setex(key, ttl_seconds or DEFAULT_TTL, payload.encode("utf-8"))
    except Exception:
        pass


def cache_delete(key: str) -> None:
    try:
        _client().delete(key)
    except Exception:
        pass


def cache_ttl(key: str) -> Optional[int]:
    try:
        ttl = _client().ttl(key)
        if ttl is None or ttl < 0:
            return None
        return int(ttl)
    except Exception:
        return None


def redis_ping() -> bool:
    try:
        return bool(_client().ping())
    except Exception:
        return False
