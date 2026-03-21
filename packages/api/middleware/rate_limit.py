"""Redis sliding-window rate limits (fail open if Redis down)."""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import settings

logger = logging.getLogger(__name__)


async def check_scan_rate_limit(user_id: str) -> bool:
    """True = allowed (at most one hit per 30s window)."""
    try:
        import redis.asyncio as redis_async
    except Exception:
        return True
    r = None
    try:
        r = redis_async.from_url(settings.redis_url, decode_responses=True)
        key = f"rate:scan:{user_id}"
        now = time.time()
        window = 30.0
        async with r.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key)
            rem, count = await pipe.execute()
        _ = rem
        if int(count) > 0:
            return False
        await r.zadd(key, {str(now): now})
        await r.expire(key, int(window * 2) + 5)
        return True
    except Exception as e:
        logger.warning("scan_rate_limit_redis_fail allow: %s", e)
        return True
    finally:
        if r is not None:
            try:
                await r.aclose()
            except Exception:
                pass


async def check_auth_ip_rate_limit(client_ip: str) -> bool:
    """100 requests per 60s per IP. True = allowed."""
    try:
        import redis.asyncio as redis_async
    except Exception:
        return True
    r = None
    try:
        r = redis_async.from_url(settings.redis_url, decode_responses=True)
        key = f"rate:auth:{client_ip}"
        now = time.time()
        window = 60.0
        max_hits = 100
        async with r.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key)
            _, count = await pipe.execute()
        if int(count) >= max_hits:
            return False
        await r.zadd(key, {str(now): now})
        await r.expire(key, int(window * 2) + 5)
        return True
    except Exception as e:
        logger.warning("auth_rate_limit_redis_fail allow: %s", e)
        return True
    finally:
        if r is not None:
            try:
                await r.aclose()
            except Exception:
                pass


class AuthIpRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path.startswith("/api/auth"):
            ip = request.client.host if request.client else "unknown"
            ok = await check_auth_ip_rate_limit(ip)
            if not ok:
                return Response(
                    content='{"error":"rate_limited","message":"Too many requests","retry_after_seconds":60}',
                    status_code=429,
                    media_type="application/json",
                )
        return await call_next(request)
