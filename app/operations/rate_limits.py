from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from app.operations.redis_runtime import RedisRuntime

_TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_per_ms = tonumber(ARGV[2])
local ttl_ms = tonumber(ARGV[3])
local now = redis.call('TIME')
local now_ms = (tonumber(now[1]) * 1000) + math.floor(tonumber(now[2]) / 1000)
local values = redis.call('HMGET', key, 'tokens', 'updated_at')
local tokens = tonumber(values[1])
local updated_at = tonumber(values[2])
if tokens == nil then tokens = capacity end
if updated_at == nil then updated_at = now_ms end
local elapsed = math.max(0, now_ms - updated_at)
tokens = math.min(capacity, tokens + (elapsed * refill_per_ms))
local allowed = 0
local retry_ms = 0
if tokens >= 1 then
  allowed = 1
  tokens = tokens - 1
else
  retry_ms = math.ceil((1 - tokens) / refill_per_ms)
end
redis.call('HSET', key, 'tokens', tokens, 'updated_at', now_ms)
redis.call('PEXPIRE', key, ttl_ms)
return {allowed, math.floor(tokens), retry_ms}
"""


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    name: str
    requests: int
    period_seconds: int
    burst: int
    fail_open: bool

    @property
    def capacity(self) -> int:
        return self.burst


POLICIES: dict[str, RateLimitPolicy] = {
    "miniapp_read": RateLimitPolicy("miniapp_read", 120, 60, 30, True),
    "miniapp_write": RateLimitPolicy("miniapp_write", 30, 60, 10, True),
    "billing": RateLimitPolicy("billing", 10, 60, 3, False),
    "owner_safe": RateLimitPolicy("owner_safe", 60, 60, 60, False),
    "owner_destructive": RateLimitPolicy("owner_destructive", 10, 60, 3, False),
    "invalid_auth": RateLimitPolicy("invalid_auth", 30, 300, 30, True),
    "scheduler": RateLimitPolicy("scheduler", 30, 60, 30, False),
}


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class RateLimitUnavailable(RuntimeError):
    pass


class RateLimitService:
    def __init__(self, runtime: RedisRuntime) -> None:
        self._runtime = runtime

    @staticmethod
    def identity_digest(policy: str, identity: str) -> str:
        return hashlib.sha256(f"{policy}\0{identity}".encode()).hexdigest()[:32]

    async def check(self, policy: str, identity: str) -> RateLimitDecision:
        selected = POLICIES.get(policy)
        if selected is None:
            raise KeyError(f"Unknown rate-limit policy: {policy}")
        if not identity:
            raise ValueError("Rate-limit identity must not be empty")
        if not self._runtime.available:
            raise RateLimitUnavailable("Redis rate limiter is unavailable")

        capacity = selected.capacity
        refill_per_ms = selected.requests / (selected.period_seconds * 1000)
        ttl_ms = max(selected.period_seconds * 2000, 1000)
        key = self._runtime.key(
            "rate",
            selected.name,
            self.identity_digest(selected.name, identity),
        )
        try:
            raw = await self._runtime.client.eval(
                _TOKEN_BUCKET_SCRIPT,
                1,
                key,
                capacity,
                refill_per_ms,
                ttl_ms,
            )
        except Exception as error:
            raise RateLimitUnavailable("Redis rate limiter failed") from error
        allowed, remaining, retry_ms = (int(raw[0]), int(raw[1]), int(raw[2]))
        return RateLimitDecision(
            allowed=bool(allowed),
            remaining=max(0, remaining),
            retry_after_seconds=max(0, math.ceil(retry_ms / 1000)),
        )
