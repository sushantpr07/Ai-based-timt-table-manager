import asyncio

from fastapi.testclient import TestClient

import app.rate_limit as rate_limit
from app.main import app
from app.rate_limit import RedisWindowLimiter


class FakeRedis:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    async def eval(self, script, number_of_keys, key, seconds, limit):
        self.calls.append((script, number_of_keys, key, seconds, limit))
        return next(self.replies)


def test_redis_limiter_uses_atomic_script_and_returns_retry_after():
    client = FakeRedis([0, 12])
    limiter = RedisWindowLimiter(client)

    first = asyncio.run(limiter.consume("sign-in:hashed-id", 10, 300))
    second = asyncio.run(limiter.consume("sign-in:hashed-id", 10, 300))

    assert first is None
    assert second == 12
    assert len(client.calls) == 2
    script, key_count, key, seconds, limit = client.calls[0]
    assert "ZREMRANGEBYSCORE" in script
    assert "redis.call('TIME')" in script
    assert key_count == 1
    assert key == "campusflow:auth-rate:sign-in:hashed-id"
    assert (seconds, limit) == (300, 10)


def test_auth_rate_limit_fails_closed_when_configured_redis_is_unavailable(monkeypatch):
    class UnavailableRedisLimiter:
        async def consume(self, key, limit, seconds):
            raise ConnectionError("redis is down")

    monkeypatch.setattr(rate_limit, "redis_limiter", UnavailableRedisLimiter())
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/sign-in", json={
            "email": "admin@example.invalid", "password": "incorrect",
        })
    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication service is temporarily unavailable."
