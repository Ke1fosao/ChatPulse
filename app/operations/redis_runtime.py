from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from app.config import Settings

logger = logging.getLogger("chatpulse.redis")


@dataclass(slots=True)
class RedisRuntime:
    _client: Redis | None
    key_prefix: str
    required: bool
    metrics: Any = None

    @classmethod
    async def create(cls, settings: Settings, *, metrics: Any = None) -> "RedisRuntime":
        prefix = settings.redis_key_prefix.rstrip(":")
        if not settings.redis_url:
            if settings.redis_required:
                raise RuntimeError("Redis is required but REDIS_URL is not configured")
            return cls(_client=None, key_prefix=prefix, required=False, metrics=metrics)

        client = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=settings.redis_connect_timeout_seconds,
            socket_timeout=settings.redis_socket_timeout_seconds,
            max_connections=settings.redis_max_connections,
            health_check_interval=30,
        )
        runtime = cls(
            _client=client,
            key_prefix=prefix,
            required=settings.redis_required,
            metrics=metrics,
        )
        try:
            await runtime.ping()
        except Exception as error:
            await runtime.close()
            logger.warning(
                "redis_startup_failed required=%s error=%s",
                settings.redis_required,
                error.__class__.__name__,
            )
            if metrics is not None:
                metrics.redis_failures.labels(operation="startup").inc()
            if settings.redis_required:
                raise RuntimeError("Required Redis dependency is unavailable") from error
            return cls(_client=None, key_prefix=prefix, required=False, metrics=metrics)
        return runtime

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis runtime is disabled or unavailable")
        return self._client

    def key(self, *parts: str | int) -> str:
        normalized = [str(part).strip(":") for part in parts]
        if not normalized or any(not part for part in normalized):
            raise ValueError("Redis keys require non-empty parts")
        return ":".join((self.key_prefix, *normalized))

    async def ping(self) -> float:
        client = self.client
        started = time.perf_counter()
        try:
            await client.ping()
        except Exception:
            if self.metrics is not None:
                self.metrics.redis_failures.labels(operation="ping").inc()
            raise
        duration = time.perf_counter() - started
        if self.metrics is not None:
            self.metrics.redis_latency.labels(operation="ping").observe(duration)
        return duration * 1000

    async def close(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            await client.aclose()

    async def execute(self, command: str, *args: Any) -> Any:
        started = time.perf_counter()
        try:
            return await self.client.execute_command(command, *args)
        except Exception:
            if self.metrics is not None:
                self.metrics.redis_failures.labels(operation=command.casefold()).inc()
            raise
        finally:
            if self.metrics is not None:
                self.metrics.redis_latency.labels(operation=command.casefold()).observe(
                    time.perf_counter() - started
                )
