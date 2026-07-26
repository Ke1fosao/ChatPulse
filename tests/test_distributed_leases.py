from __future__ import annotations

from typing import Any

import pytest

from app.operations.leases import LeaseService
from app.operations.redis_runtime import RedisRuntime


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expiries: dict[str, int] = {}

    async def set(
        self,
        key: str,
        value: str,
        *,
        nx: bool,
        px: int,
    ) -> bool:
        if nx and key in self.values:
            return False
        self.values[key] = value
        self.expiries[key] = px
        return True

    async def eval(self, script: str, keys_count: int, *args: Any) -> int:
        assert keys_count == 1
        key = str(args[0])
        token = str(args[1])
        if self.values.get(key) != token:
            return 0
        if "-- release" in script:
            self.values.pop(key, None)
            self.expiries.pop(key, None)
            return 1
        if "-- renew" in script:
            self.expiries[key] = int(args[2])
            return 1
        raise AssertionError("unknown script")


@pytest.fixture
def lease_service() -> tuple[LeaseService, FakeRedis]:
    client = FakeRedis()
    runtime = RedisRuntime(
        _client=client,  # type: ignore[arg-type]
        key_prefix="chatpulse:test",
        required=True,
    )
    return LeaseService(runtime), client


async def test_only_one_instance_acquires_the_same_lease(
    lease_service: tuple[LeaseService, FakeRedis],
) -> None:
    service, _ = lease_service

    first = await service.acquire("weekly-reports-2026-31", 120)
    second = await service.acquire("weekly-reports-2026-31", 120)

    assert first.acquired is True
    assert second.acquired is False
    assert first.token != second.token


async def test_owner_can_renew_and_release_lease(
    lease_service: tuple[LeaseService, FakeRedis],
) -> None:
    service, client = lease_service
    handle = await service.acquire("vip-lifecycle-2026-07-26", 60)
    key = "chatpulse:test:lease:vip-lifecycle-2026-07-26"

    assert await handle.renew() is True
    assert client.expiries[key] == 60_000
    assert await handle.release() is True
    assert key not in client.values
    assert handle.acquired is False


async def test_foreign_token_cannot_release_or_renew(
    lease_service: tuple[LeaseService, FakeRedis],
) -> None:
    service, client = lease_service
    handle = await service.acquire("retention-2026-07-26", 60)
    key = "chatpulse:test:lease:retention-2026-07-26"
    client.values[key] = "foreign-owner-token"

    assert await handle.renew() is False
    assert handle.acquired is False
    assert client.values[key] == "foreign-owner-token"


async def test_unavailable_redis_fails_closed_for_singleton_job() -> None:
    runtime = RedisRuntime(_client=None, key_prefix="chatpulse:test", required=False)
    service = LeaseService(runtime)

    handle = await service.acquire("weekly-reports-2026-31", 120)

    assert handle.acquired is False
    assert await handle.renew() is False
    assert await handle.release() is False


@pytest.mark.parametrize("ttl", [0, 3601])
async def test_invalid_ttl_is_rejected(ttl: int) -> None:
    runtime = RedisRuntime(_client=None, key_prefix="chatpulse:test", required=False)
    service = LeaseService(runtime)

    with pytest.raises(ValueError, match="TTL"):
        await service.acquire("weekly-reports", ttl)


@pytest.mark.parametrize("name", ["", "weekly:reports"])
async def test_invalid_name_is_rejected(name: str) -> None:
    runtime = RedisRuntime(_client=None, key_prefix="chatpulse:test", required=False)
    service = LeaseService(runtime)

    with pytest.raises(ValueError, match="name"):
        await service.acquire(name, 60)
