from __future__ import annotations

from typing import Any

import pytest

from app.config import Settings
from app.operations.redis_runtime import RedisRuntime


class FakeRedis:
    def __init__(self, *, fail_ping: bool = False) -> None:
        self.fail_ping = fail_ping
        self.closed = False
        self.ping_calls = 0

    async def ping(self) -> bool:
        self.ping_calls += 1
        if self.fail_ping:
            raise ConnectionError("redis unavailable")
        return True

    async def aclose(self) -> None:
        self.closed = True


def settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "bot_token": "123456:test-token",
        "webhook_path_secret": "path-secret",
        "webhook_header_secret": "header-secret",
        "database_url": "sqlite+aiosqlite:///:memory:",
    }
    values.update(overrides)
    return Settings(**values)


async def test_optional_redis_without_url_is_disabled() -> None:
    runtime = await RedisRuntime.create(settings())

    assert runtime.available is False
    assert runtime.key("lease", 12) == "chatpulse:v1:lease:12"


async def test_required_redis_without_url_fails_startup() -> None:
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        await RedisRuntime.create(settings(redis_required=True))


async def test_runtime_uses_bounded_client_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRedis()
    captured: dict[str, Any] = {}

    def fake_from_url(url: str, **kwargs: Any) -> FakeRedis:
        captured["url"] = url
        captured.update(kwargs)
        return fake

    monkeypatch.setattr("app.operations.redis_runtime.Redis.from_url", fake_from_url)
    runtime = await RedisRuntime.create(
        settings(
            redis_url="redis://cache.internal:6379/0",
            redis_required=True,
            redis_key_prefix="chatpulse:test:",
            redis_connect_timeout_seconds=1.5,
            redis_socket_timeout_seconds=1.25,
            redis_max_connections=7,
        )
    )

    assert runtime.available is True
    assert runtime.key("rate", "read", 42) == "chatpulse:test:rate:read:42"
    assert captured == {
        "url": "redis://cache.internal:6379/0",
        "encoding": "utf-8",
        "decode_responses": True,
        "socket_connect_timeout": 1.5,
        "socket_timeout": 1.25,
        "max_connections": 7,
        "health_check_interval": 30,
    }
    assert fake.ping_calls == 1

    await runtime.close()
    assert runtime.available is False
    assert fake.closed is True


async def test_optional_redis_failure_degrades_to_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeRedis(fail_ping=True)
    monkeypatch.setattr(
        "app.operations.redis_runtime.Redis.from_url",
        lambda *args, **kwargs: fake,
    )

    runtime = await RedisRuntime.create(settings(redis_url="redis://unavailable"))

    assert runtime.available is False
    assert fake.closed is True


async def test_required_redis_failure_fails_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRedis(fail_ping=True)
    monkeypatch.setattr(
        "app.operations.redis_runtime.Redis.from_url",
        lambda *args, **kwargs: fake,
    )

    with pytest.raises(RuntimeError, match="Required Redis"):
        await RedisRuntime.create(
            settings(redis_url="rediss://unavailable", redis_required=True)
        )

    assert fake.closed is True


def test_key_rejects_empty_parts() -> None:
    runtime = RedisRuntime(_client=None, key_prefix="chatpulse:v1", required=False)

    with pytest.raises(ValueError):
        runtime.key("lease", "")
