from __future__ import annotations

from typing import Any

import pytest

from app.operations.rate_limits import POLICIES, RateLimitService, RateLimitUnavailable
from app.operations.redis_runtime import RedisRuntime


class FakeRedis:
    def __init__(self, replies: list[list[int]] | None = None, *, error: Exception | None = None):
        self.replies = replies or [[1, 29, 0]]
        self.error = error
        self.calls: list[tuple[Any, ...]] = []

    async def eval(self, *args: Any) -> list[int]:
        self.calls.append(args)
        if self.error:
            raise self.error
        return self.replies.pop(0)


async def test_rate_limit_returns_atomic_decision_and_hashed_key() -> None:
    client = FakeRedis([[1, 7, 0], [0, 0, 1250]])
    service = RateLimitService(
        RedisRuntime(_client=client, key_prefix="chatpulse:test", required=True)  # type: ignore[arg-type]
    )

    allowed = await service.check("miniapp_write", "telegram-user-123")
    rejected = await service.check("miniapp_write", "telegram-user-123")

    assert allowed.allowed is True
    assert allowed.remaining == 7
    assert rejected.allowed is False
    assert rejected.retry_after_seconds == 2
    key = client.calls[0][2]
    assert str(key).startswith("chatpulse:test:rate:miniapp_write:")
    assert "telegram-user-123" not in str(key)


@pytest.mark.parametrize(
    ("name", "requests", "period", "burst", "fail_open"),
    [
        ("miniapp_read", 120, 60, 30, True),
        ("miniapp_write", 30, 60, 10, True),
        ("billing", 10, 60, 3, False),
        ("owner_safe", 60, 60, 60, False),
        ("owner_destructive", 10, 60, 3, False),
        ("invalid_auth", 30, 300, 30, True),
        ("scheduler", 30, 60, 30, False),
    ],
)
def test_rate_limit_policies_match_production_contract(
    name: str,
    requests: int,
    period: int,
    burst: int,
    fail_open: bool,
) -> None:
    policy = POLICIES[name]
    assert policy.requests == requests
    assert policy.period_seconds == period
    assert policy.burst == burst
    assert policy.capacity == burst
    assert policy.fail_open is fail_open


async def test_rate_limit_passes_burst_capacity_and_refill_rate_to_lua() -> None:
    client = FakeRedis([[1, 2, 0]])
    service = RateLimitService(
        RedisRuntime(_client=client, key_prefix="chatpulse:test", required=True)  # type: ignore[arg-type]
    )

    await service.check("billing", "123")

    call = client.calls[0]
    assert call[3] == 3
    assert call[4] == pytest.approx(10 / 60_000)
    assert call[5] == 120_000


async def test_rate_limit_unavailable_is_explicit() -> None:
    service = RateLimitService(
        RedisRuntime(_client=None, key_prefix="chatpulse:test", required=False)
    )
    with pytest.raises(RateLimitUnavailable):
        await service.check("billing", "123")


async def test_rate_limit_wraps_redis_errors() -> None:
    client = FakeRedis(error=ConnectionError("secret endpoint"))
    service = RateLimitService(
        RedisRuntime(_client=client, key_prefix="chatpulse:test", required=True)  # type: ignore[arg-type]
    )
    with pytest.raises(RateLimitUnavailable, match="failed"):
        await service.check("billing", "123")
