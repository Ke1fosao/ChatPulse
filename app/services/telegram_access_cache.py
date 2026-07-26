from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Hashable
from dataclasses import dataclass

logger = logging.getLogger("chatpulse.telegram_access")


@dataclass(frozen=True, slots=True)
class CachedTelegramStatus[T]:
    value: T | None
    fresh: bool
    stale: bool


@dataclass(slots=True)
class _CacheEntry[T]:
    value: T | None
    fresh_until: float
    stale_until: float


class TelegramAccessCache[T]:
    """Small in-memory TTL/LRU cache with stale-on-error and miss coalescing."""

    def __init__(
        self,
        *,
        max_entries: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[Hashable, _CacheEntry[T]] = OrderedDict()
        self._inflight: dict[Hashable, asyncio.Task[T | None]] = {}
        self._lock = asyncio.Lock()

    async def get_or_load(
        self,
        key: Hashable,
        loader: Callable[[], Awaitable[T | None]],
        *,
        positive_ttl: float,
        negative_ttl: float,
        stale_grace: float,
        is_negative: Callable[[T | None], bool] | None = None,
    ) -> CachedTelegramStatus[T]:
        negative = is_negative or (lambda value: value is None)
        now = self._clock()
        stale_entry: _CacheEntry[T] | None = None
        created = False

        async with self._lock:
            entry = self._entries.get(key)
            if entry is not None:
                if now <= entry.fresh_until:
                    self._entries.move_to_end(key)
                    logger.debug("telegram_access_cache_hit key=%r", key)
                    return CachedTelegramStatus(entry.value, fresh=True, stale=False)
                if now <= entry.stale_until:
                    stale_entry = entry
                else:
                    self._entries.pop(key, None)

            task = self._inflight.get(key)
            if task is None:
                task = asyncio.create_task(loader())
                self._inflight[key] = task
                created = True
                logger.debug("telegram_access_cache_miss key=%r", key)

        try:
            value = await task
        except Exception:
            async with self._lock:
                if created and self._inflight.get(key) is task:
                    self._inflight.pop(key, None)
                current = self._entries.get(key)
                if current is not None and self._clock() <= current.stale_until:
                    stale_entry = current
                    self._entries.move_to_end(key)
            if stale_entry is not None:
                logger.warning("telegram_access_cache_stale key=%r", key)
                return CachedTelegramStatus(stale_entry.value, fresh=False, stale=True)
            logger.warning("telegram_access_cache_load_failed key=%r", key)
            return CachedTelegramStatus(None, fresh=False, stale=False)

        now = self._clock()
        ttl = negative_ttl if negative(value) else positive_ttl
        entry = _CacheEntry(
            value=value,
            fresh_until=now + max(0.0, ttl),
            stale_until=now + max(0.0, ttl) + max(0.0, stale_grace),
        )
        async with self._lock:
            if created and self._inflight.get(key) is task:
                self._inflight.pop(key, None)
            self._entries[key] = entry
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                evicted_key, _ = self._entries.popitem(last=False)
                logger.debug("telegram_access_cache_evicted key=%r", evicted_key)
        return CachedTelegramStatus(value, fresh=True, stale=False)

    async def invalidate(self, predicate: Callable[[Hashable], bool]) -> None:
        async with self._lock:
            for key in [candidate for candidate in self._entries if predicate(candidate)]:
                self._entries.pop(key, None)

    async def invalidate_user(self, chat_id: int, user_id: int) -> None:
        await self.invalidate(
            lambda key: (
                isinstance(key, tuple) and len(key) >= 3 and key[1] == chat_id and key[2] == user_id
            )
        )

    async def invalidate_group(self, chat_id: int) -> None:
        await self.invalidate(
            lambda key: isinstance(key, tuple) and len(key) >= 2 and key[1] == chat_id
        )

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()

    async def size(self) -> int:
        async with self._lock:
            return len(self._entries)
