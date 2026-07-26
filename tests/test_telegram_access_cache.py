import asyncio
from dataclasses import dataclass

import pytest

from app.services.telegram_access_cache import TelegramAccessCache


@dataclass
class Clock:
    value: float = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


@pytest.mark.asyncio
async def test_cache_uses_positive_and_negative_ttls() -> None:
    clock = Clock()
    cache: TelegramAccessCache[str] = TelegramAccessCache(clock=clock)
    calls = 0

    async def positive() -> str:
        nonlocal calls
        calls += 1
        return "member"

    assert (await cache.get_or_load(
        ("member", 1, 2), positive,
        positive_ttl=60, negative_ttl=15, stale_grace=300,
    )).value == "member"
    clock.advance(59)
    assert (await cache.get_or_load(
        ("member", 1, 2), positive,
        positive_ttl=60, negative_ttl=15, stale_grace=300,
    )).fresh is True
    assert calls == 1
    clock.advance(2)
    await cache.get_or_load(
        ("member", 1, 2), positive,
        positive_ttl=60, negative_ttl=15, stale_grace=300,
    )
    assert calls == 2

    negative_calls = 0

    async def negative() -> None:
        nonlocal negative_calls
        negative_calls += 1
        return None

    await cache.get_or_load(
        ("member", 2, 3), negative,
        positive_ttl=60, negative_ttl=15, stale_grace=300,
    )
    clock.advance(14)
    await cache.get_or_load(
        ("member", 2, 3), negative,
        positive_ttl=60, negative_ttl=15, stale_grace=300,
    )
    assert negative_calls == 1
    clock.advance(2)
    await cache.get_or_load(
        ("member", 2, 3), negative,
        positive_ttl=60, negative_ttl=15, stale_grace=300,
    )
    assert negative_calls == 2


@pytest.mark.asyncio
async def test_cache_coalesces_concurrent_misses() -> None:
    cache: TelegramAccessCache[str] = TelegramAccessCache()
    calls = 0
    release = asyncio.Event()

    async def loader() -> str:
        nonlocal calls
        calls += 1
        await release.wait()
        return "administrator"

    tasks = [
        asyncio.create_task(cache.get_or_load(
            ("member", 1, 2), loader,
            positive_ttl=60, negative_ttl=15, stale_grace=300,
        ))
        for _ in range(20)
    ]
    await asyncio.sleep(0)
    assert calls == 1
    release.set()
    results = await asyncio.gather(*tasks)
    assert {item.value for item in results} == {"administrator"}


@pytest.mark.asyncio
async def test_cache_uses_stale_value_when_loader_fails() -> None:
    clock = Clock()
    cache: TelegramAccessCache[str] = TelegramAccessCache(clock=clock)

    async def initial() -> str:
        return "member"

    await cache.get_or_load(
        ("member", 1, 2), initial,
        positive_ttl=60, negative_ttl=15, stale_grace=300,
    )
    clock.advance(61)

    async def failing() -> str:
        raise RuntimeError("Telegram unavailable")

    result = await cache.get_or_load(
        ("member", 1, 2), failing,
        positive_ttl=60, negative_ttl=15, stale_grace=300,
    )
    assert result.value == "member"
    assert result.stale is True
    assert result.fresh is False

    clock.advance(301)
    result = await cache.get_or_load(
        ("member", 1, 2), failing,
        positive_ttl=60, negative_ttl=15, stale_grace=300,
    )
    assert result.value is None
    assert result.stale is False


@pytest.mark.asyncio
async def test_cache_evicts_lru_and_supports_invalidation() -> None:
    cache: TelegramAccessCache[str] = TelegramAccessCache(max_entries=2)

    async def load(value: str) -> str:
        return value

    for key, value in [(("member", 1, 1), "a"), (("member", 1, 2), "b")]:
        await cache.get_or_load(
            key, lambda value=value: load(value),
            positive_ttl=60, negative_ttl=15, stale_grace=300,
        )
    await cache.get_or_load(
        ("member", 1, 1), lambda: load("a"),
        positive_ttl=60, negative_ttl=15, stale_grace=300,
    )
    await cache.get_or_load(
        ("member", 2, 3), lambda: load("c"),
        positive_ttl=60, negative_ttl=15, stale_grace=300,
    )
    assert await cache.size() == 2

    await cache.invalidate_user(1, 1)
    assert await cache.size() == 1
    await cache.invalidate_group(2)
    assert await cache.size() == 0
