from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.middlewares.user_restrictions import BlockedUserMiddleware


@pytest.mark.asyncio
async def test_blocked_group_user_never_reaches_handler() -> None:
    repository = SimpleNamespace(
        is_blocked=AsyncMock(return_value=True),
        record_blocked_access=AsyncMock(),
    )
    middleware = BlockedUserMiddleware(repository)
    handler = AsyncMock(return_value="handled")
    event = SimpleNamespace(
        from_user=SimpleNamespace(id=202),
        chat=SimpleNamespace(type="supergroup"),
    )

    result = await middleware(handler, event, {})

    assert result is None
    handler.assert_not_awaited()
    repository.record_blocked_access.assert_awaited_once_with(202, "bot_group")


@pytest.mark.asyncio
async def test_active_user_reaches_handler() -> None:
    repository = SimpleNamespace(
        is_blocked=AsyncMock(return_value=False),
        record_blocked_access=AsyncMock(),
    )
    middleware = BlockedUserMiddleware(repository)
    handler = AsyncMock(return_value="handled")
    event = SimpleNamespace(
        from_user=SimpleNamespace(id=202),
        chat=SimpleNamespace(type="private"),
    )

    result = await middleware(handler, event, {})

    assert result == "handled"
    handler.assert_awaited_once_with(event, {})
    repository.record_blocked_access.assert_not_awaited()
