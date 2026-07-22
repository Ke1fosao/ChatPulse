from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.routers.settings import is_group_admin
from app.services.telegram_access import TelegramAccessService


@pytest.mark.asyncio
async def test_owner_bypasses_group_admin_check_in_bot() -> None:
    bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=RuntimeError("not needed")))
    owner_repository = SimpleNamespace(is_owner=AsyncMock(return_value=True))

    allowed = await is_group_admin(
        bot,
        chat_id=-1001,
        user_id=101,
        owner_repository=owner_repository,
    )

    assert allowed is True
    bot.get_chat_member.assert_not_awaited()


@pytest.mark.asyncio
async def test_owner_bypasses_group_admin_check_in_miniapp() -> None:
    bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=RuntimeError("not needed")))
    owner_repository = SimpleNamespace(is_owner=AsyncMock(return_value=True))
    service = TelegramAccessService(bot, owner_repository=owner_repository)

    assert await service.check_admin(-1001, 101) is True
    bot.get_chat_member.assert_not_awaited()


@pytest.mark.asyncio
async def test_regular_user_still_uses_telegram_admin_status() -> None:
    bot = SimpleNamespace(
        get_chat_member=AsyncMock(return_value=SimpleNamespace(status="administrator"))
    )
    owner_repository = SimpleNamespace(is_owner=AsyncMock(return_value=False))
    service = TelegramAccessService(bot, owner_repository=owner_repository)

    assert await service.check_admin(-1001, 202) is True
    bot.get_chat_member.assert_awaited_once_with(-1001, 202)
