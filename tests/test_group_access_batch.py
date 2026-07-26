import asyncio

import pytest

from app.api.miniapp.access import resolve_group_access


class FakeAccessService:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.calls: list[tuple[str, int]] = []

    async def _run(self, kind: str, chat_id: int, value):
        self.calls.append((kind, chat_id))
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.001)
        self.active -= 1
        return value

    async def check_member(self, chat_id: int, _user_id: int) -> bool:
        return await self._run("member", chat_id, True)

    async def check_admin(self, chat_id: int, _user_id: int) -> bool:
        return await self._run("admin", chat_id, chat_id % 2 == 0)

    async def get_bot_status(self, chat_id: int) -> str:
        return await self._run("bot", chat_id, "administrator")


@pytest.mark.asyncio
async def test_group_access_is_concurrent_bounded_and_deduplicated() -> None:
    service = FakeAccessService()
    chat_ids = list(range(30)) + [1, 2, 3]

    result = await resolve_group_access(
        service,
        user_id=101,
        chat_ids=chat_ids,
        concurrency=8,
    )

    assert set(result) == set(range(30))
    assert 1 < service.max_active <= 8
    assert service.calls.count(("member", 1)) == 1
    assert service.calls.count(("admin", 1)) == 1
    assert service.calls.count(("bot", 1)) == 1
