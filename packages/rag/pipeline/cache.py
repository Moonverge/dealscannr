"""Pipeline cache: Redis → diskcache → skip (silent fallback, never blocks)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_redis_client: Any = None
_redis_checked = False
_disk_cache: Any = None
_disk_checked = False

EMBEDDING_TTL = 7 * 86400  # 7 days
REPORT_TTL = 24 * 3600  # 24 hours


def _get_redis() -> Any:
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        import redis as _redis

        url = os.environ.get("REDIS_URL", "redis://localhost:5400")
        _redis_client = _redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.debug("redis_cache_unavailable: %s", e)
        _redis_client = None
        return None


def _get_diskcache() -> Any:
    global _disk_cache, _disk_checked
    if _disk_checked:
        return _disk_cache
    _disk_checked = True
    try:
        import diskcache

        _disk_cache = diskcache.Cache(
            os.environ.get("DISKCACHE_DIR", "/tmp/dealscannr_cache")
        )
        return _disk_cache
    except Exception as e:
        logger.debug("diskcache_unavailable: %s", e)
        _disk_cache = None
        return None


def cache_get(key: str) -> Any | None:
    r = _get_redis()
    if r is not None:
        try:
            val = r.get(key)
            if val is not None:
                return json.loads(val)
        except Exception:
            pass
    d = _get_diskcache()
    if d is not None:
        try:
            val = d.get(key)
            if val is not None:
                return json.loads(val) if isinstance(val, str) else val
        except Exception:
            pass
    return None


def cache_set(key: str, value: Any, ttl_seconds: int = REPORT_TTL) -> None:
    serialized = json.dumps(value, default=str)
    r = _get_redis()
    if r is not None:
        try:
            r.setex(key, ttl_seconds, serialized)
            return
        except Exception:
            pass
    d = _get_diskcache()
    if d is not None:
        try:
            d.set(key, serialized, expire=ttl_seconds)
        except Exception:
            pass


def embedding_cache_key(slug: str, text_hash: str) -> str:
    return f"ds:emb:{slug}:{text_hash}"


def report_cache_key(slug: str) -> str:
    return f"ds:report:{slug}"


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
