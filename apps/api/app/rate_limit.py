import hashlib
import json
import threading
import time
from collections import deque
import logging

from redis.asyncio import Redis

from fastapi import HTTPException, Request
from app.core.config import settings


class WindowLimiter:
    """Small per-process fallback for local development without Redis."""

    def __init__(self):
        self._windows: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def consume(self, key: str, limit: int, seconds: int) -> int | None:
        now = time.monotonic()
        with self._lock:
            window = self._windows.setdefault(key, deque())
            while window and now - window[0] >= seconds:
                window.popleft()
            if len(window) >= limit:
                return max(1, int(seconds - (now - window[0])))
            window.append(now)
            if len(self._windows) > 10000:
                expired = [name for name, events in self._windows.items()
                           if not events or now - events[-1] >= seconds]
                for name in expired:
                    self._windows.pop(name, None)
            return None


auth_limiter = WindowLimiter()
logger = logging.getLogger("campusflow.rate_limit")


class RedisWindowLimiter:
    """Atomic shared sliding-window limiter backed by Redis sorted sets."""

    _SCRIPT = """
local time_parts = redis.call('TIME')
local now = tonumber(time_parts[1]) * 1000 + math.floor(tonumber(time_parts[2]) / 1000)
local window = tonumber(ARGV[1]) * 1000
local limit = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
local count = redis.call('ZCARD', KEYS[1])
if count >= limit then
  local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
  return math.max(1, math.ceil((tonumber(oldest[2]) + window - now) / 1000))
end
local sequence = redis.call('INCR', KEYS[1] .. ':sequence')
redis.call('ZADD', KEYS[1], now, tostring(now) .. ':' .. tostring(sequence))
redis.call('PEXPIRE', KEYS[1], window)
redis.call('PEXPIRE', KEYS[1] .. ':sequence', window)
return 0
"""

    def __init__(self, client: Redis):
        self._client = client

    async def consume(self, key: str, limit: int, seconds: int) -> int | None:
        retry_after = await self._client.eval(self._SCRIPT, 1, f"campusflow:auth-rate:{key}", seconds, limit)
        value = int(retry_after)
        return value if value > 0 else None

    async def close(self) -> None:
        await self._client.aclose()

    async def ping(self) -> bool:
        return bool(await self._client.ping())


redis_limiter = (RedisWindowLimiter(Redis.from_url(settings.rate_limit_redis_url))
                 if settings.rate_limit_redis_url else None)


def limit_auth_requests(action: str, limit: int, seconds: int):
    async def enforce(request: Request):
        identity = ""
        try:
            body = await request.json()
            if isinstance(body, dict):
                identity = str(body.get("email", "")).strip().lower()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            pass
        if not identity:
            identity = request.client.host if request.client else "unknown-client"
        identity_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        key = f"{action}:{identity_hash}"
        try:
            retry_after = (await redis_limiter.consume(key, limit, seconds) if redis_limiter
                           else auth_limiter.consume(key, limit, seconds))
        except Exception as exc:
            logger.error("shared auth limiter unavailable error_type=%s", type(exc).__name__)
            raise HTTPException(status_code=503, detail="Authentication service is temporarily unavailable.")
        if retry_after is not None:
            raise HTTPException(status_code=429, detail="Too many requests. Try again later.",
                                headers={"Retry-After": str(retry_after)})

    return enforce
