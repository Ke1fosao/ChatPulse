from __future__ import annotations

import asyncio
import logging
import re
import secrets
from dataclasses import dataclass, field
from typing import Any

from app.operations.redis_runtime import RedisRuntime

logger = logging.getLogger("chatpulse.leases")
_LEASE_NAME = re.compile(r"^[A-Za-z0-9._-]{1,160}$")

_RELEASE_SCRIPT = """
-- release
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""

_RENEW_SCRIPT = """
-- renew
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('pexpire', KEYS[1], ARGV[2])
end
return 0
"""


@dataclass(slots=True)
class LeaseHandle:
    name: str
    token: str
    ttl_ms: int
    acquired: bool
    _service: "LeaseService"
    _renew_task: asyncio.Task[None] | None = field(default=None, init=False, repr=False)

    async def renew(self) -> bool:
        if not self.acquired:
            return False
        renewed = await self._service._renew(self)
        if not renewed:
            self.acquired = False
        return renewed

    async def release(self) -> bool:
        if self._renew_task is not None:
            self._renew_task.cancel()
            try:
                await self._renew_task
            except asyncio.CancelledError:
                pass
            self._renew_task = None
        if not self.acquired:
            return False
        released = await self._service._release(self)
        self.acquired = False
        return released

    async def _keep_alive(self) -> None:
        interval = max(1.0, min(60.0, self.ttl_ms / 3000))
        try:
            while self.acquired:
                await asyncio.sleep(interval)
                if not await self.renew():
                    logger.warning("distributed_lease_lost name=%s", self.name)
                    return
        except asyncio.CancelledError:
            raise

    async def __aenter__(self) -> "LeaseHandle":
        if self.acquired and self.ttl_ms >= 3000:
            self._renew_task = asyncio.create_task(self._keep_alive())
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.release()


class LeaseService:
    def __init__(self, runtime: RedisRuntime, *, metrics: Any = None) -> None:
        self._runtime = runtime
        self._metrics = metrics

    def _record(self, name: str, outcome: str) -> None:
        if self._metrics is not None:
            operation = name.split(":", 1)[0].split("-", 1)[0]
            self._metrics.leases.labels(operation=operation, outcome=outcome).inc()

    async def acquire(self, name: str, ttl_seconds: int) -> LeaseHandle:
        if not _LEASE_NAME.fullmatch(name):
            raise ValueError("Lease name contains unsupported characters")
        if not 1 <= ttl_seconds <= 3600:
            raise ValueError("Lease TTL must be between 1 and 3600 seconds")

        ttl_ms = ttl_seconds * 1000
        token = secrets.token_urlsafe(24)
        handle = LeaseHandle(name=name, token=token, ttl_ms=ttl_ms, acquired=False, _service=self)
        if not self._runtime.available:
            logger.warning("distributed_lease_skipped name=%s reason=redis_unavailable", name)
            self._record(name, "unavailable")
            return handle

        key = self._runtime.key("lease", name)
        try:
            result = await self._runtime.client.set(key, token, nx=True, px=ttl_ms)
        except Exception:
            logger.exception("distributed_lease_failed name=%s", name)
            self._record(name, "failed")
            return handle
        handle.acquired = bool(result)
        self._record(name, "acquired" if handle.acquired else "skipped")
        return handle

    async def _renew(self, handle: LeaseHandle) -> bool:
        if not self._runtime.available:
            self._record(handle.name, "lost")
            return False
        key = self._runtime.key("lease", handle.name)
        try:
            result = await self._runtime.client.eval(
                _RENEW_SCRIPT,
                1,
                key,
                handle.token,
                handle.ttl_ms,
            )
        except Exception:
            self._record(handle.name, "lost")
            return False
        renewed = bool(result)
        self._record(handle.name, "renewed" if renewed else "lost")
        return renewed

    async def _release(self, handle: LeaseHandle) -> bool:
        if not self._runtime.available:
            return False
        key = self._runtime.key("lease", handle.name)
        try:
            result = await self._runtime.client.eval(
                _RELEASE_SCRIPT,
                1,
                key,
                handle.token,
            )
        except Exception:
            self._record(handle.name, "release_failed")
            return False
        released = bool(result)
        self._record(handle.name, "released" if released else "foreign_token")
        return released
