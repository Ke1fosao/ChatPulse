from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass

from app.operations.redis_runtime import RedisRuntime

logger = logging.getLogger("chatpulse.leases")

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
    _service: LeaseService

    async def renew(self) -> bool:
        if not self.acquired:
            return False
        renewed = await self._service._renew(self)
        if not renewed:
            self.acquired = False
        return renewed

    async def release(self) -> bool:
        if not self.acquired:
            return False
        released = await self._service._release(self)
        self.acquired = False
        return released

    async def __aenter__(self) -> LeaseHandle:
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.release()


class LeaseService:
    def __init__(self, runtime: RedisRuntime) -> None:
        self._runtime = runtime

    async def acquire(self, name: str, ttl_seconds: int) -> LeaseHandle:
        if not name or ":" in name:
            raise ValueError("Lease name must be a non-empty operation identifier")
        if not 1 <= ttl_seconds <= 3600:
            raise ValueError("Lease TTL must be between 1 and 3600 seconds")

        ttl_ms = ttl_seconds * 1000
        token = secrets.token_urlsafe(24)
        handle = LeaseHandle(
            name=name,
            token=token,
            ttl_ms=ttl_ms,
            acquired=False,
            _service=self,
        )
        if not self._runtime.available:
            logger.warning("distributed_lease_skipped name=%s reason=redis_unavailable", name)
            return handle

        key = self._runtime.key("lease", name)
        result = await self._runtime.client.set(key, token, nx=True, px=ttl_ms)
        handle.acquired = bool(result)
        return handle

    async def _renew(self, handle: LeaseHandle) -> bool:
        if not self._runtime.available:
            return False
        key = self._runtime.key("lease", handle.name)
        result = await self._runtime.client.eval(
            _RENEW_SCRIPT,
            1,
            key,
            handle.token,
            handle.ttl_ms,
        )
        return bool(result)

    async def _release(self, handle: LeaseHandle) -> bool:
        if not self._runtime.available:
            return False
        key = self._runtime.key("lease", handle.name)
        result = await self._runtime.client.eval(
            _RELEASE_SCRIPT,
            1,
            key,
            handle.token,
        )
        return bool(result)
