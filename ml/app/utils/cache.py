from __future__ import annotations

import json
import os
from typing import Any, Optional

CACHE_ENABLED = os.getenv("CACHE_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DEFAULT_TTL = int(os.getenv("CACHE_TTL_SECONDS", "1800"))

_redis_client = None


def _client():
    """Lazily connect to Redis - and only if caching is enabled, so `redis` is never
    imported (let alone dialed) when CACHE_ENABLED is false. Nothing in the MVP
    recommendation loop requires a cache; see docs/SPEC.md §1/§4.4."""
    global _redis_client
    if not CACHE_ENABLED:
        return None
    if _redis_client is not None:
        return _redis_client
    import redis  # optional dependency - only imported when caching is enabled

    _redis_client = redis.from_url(
        REDIS_URL,
        socket_timeout=0.4,
        retry_on_timeout=True,
        health_check_interval=30,
        decode_responses=False,
    )
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    client = _client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
    client = _client()
    if client is None:
        return
    try:
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        client.setex(key, ttl_seconds or DEFAULT_TTL, payload.encode("utf-8"))
    except Exception:
        pass


def cache_delete(key: str) -> None:
    client = _client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception:
        pass


def cache_delete_prefix(prefix: str) -> None:
    client = _client()
    if client is None:
        return
    try:
        for k in client.scan_iter(match=f"{prefix}*"):
            try:
                client.delete(k)
            except Exception:
                pass
    except Exception:
        pass


def redis_ping() -> bool:
    client = _client()
    if client is None:
        return True  # caching disabled is not a failure state
    try:
        return bool(client.ping())
    except Exception:
        return False
