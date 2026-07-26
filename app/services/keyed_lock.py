from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Hashable
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass(slots=True)
class _LockEntry:
    lock: asyncio.Lock
    users: int = 0


class KeyedAsyncLock:
    """Serialize same-process work for one logical database resource."""

    def __init__(self) -> None:
        self._entries: dict[Hashable, _LockEntry] = {}
        self._guard = asyncio.Lock()

    @asynccontextmanager
    async def hold(self, key: Hashable) -> AsyncIterator[None]:
        async with self._guard:
            entry = self._entries.get(key)
            if entry is None:
                entry = _LockEntry(asyncio.Lock())
                self._entries[key] = entry
            entry.users += 1

        try:
            async with entry.lock:
                yield
        finally:
            async with self._guard:
                entry.users -= 1
                if entry.users == 0 and not entry.lock.locked():
                    self._entries.pop(key, None)
