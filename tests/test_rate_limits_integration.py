from __future__ import annotations

import asyncio
import os
import uuid

import pytest

from app.config import Settings
from app.operations.leases import LeaseService
from app.operations.rate_limits import RateLimitService
from app.operations.redis_runtime import RedisRuntime

pytestmark = pytest.mark.skipif(not os.getenv("TEST_REDIS_URL"), reason="Redis integration URL absent")


def settings(prefix: str) -> Settings:
    return Settings(
        bot_token="123456:test-token",
        webhook_path_secret="path-secret",
        webhook_header_secret="header-secret",
        redis_url=os.environ["TEST_REDIS_URL"],
        redis_required=True,
        redis_key_prefix=prefix,
    )


async def test_atomic_burst_allows_exactly_configured_capacity() -> None:
    runtime = await RedisRuntime.create(settings(f"chatpulse:test:{uuid.uuid4().hex}"))
    try:
        service = RateLimitService(runtime)
        decisions = await asyncio.gather(
            *(service.check("billing", "same-user") for _ in range(12))
        )
        assert sum(decision.allowed for decision in decisions) == 3
        assert any(decision.retry_after_seconds >= 1 for decision in decisions if not decision.allowed)
    finally:
        await runtime.close()


async def test_two_instances_cannot_hold_same_scheduler_lease() -> None:
    prefix = f"chatpulse:test:{uuid.uuid4().hex}"
    first_runtime = await RedisRuntime.create(settings(prefix))
    second_runtime = await RedisRuntime.create(settings(prefix))
    try:
        first, second = LeaseService(first_runtime), LeaseService(second_runtime)
        handles = await asyncio.gather(
            first.acquire("weekly-reports-integration", 30),
            second.acquire("weekly-reports-integration", 30),
        )
        assert sum(handle.acquired for handle in handles) == 1
        owner = next(handle for handle in handles if handle.acquired)
        assert await owner.release() is True
    finally:
        await first_runtime.close()
        await second_runtime.close()
