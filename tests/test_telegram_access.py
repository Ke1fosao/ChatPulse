from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.telegram_access import TelegramAccessService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "is_member", "expected_member", "expected_admin"),
    [
        ("creator", None, True, True),
        ("administrator", None, True, True),
        ("member", None, True, False),
        ("restricted", True, True, False),
        ("restricted", False, False, False),
        ("left", None, False, False),
        ("kicked", None, False, False),
    ],
)
async def test_telegram_access_rules(
    status: str,
    is_member: bool | None,
    expected_member: bool,
    expected_admin: bool,
) -> None:
    bot = SimpleNamespace(
        get_chat_member=AsyncMock(
            return_value=SimpleNamespace(status=status, is_member=is_member)
        )
    )
    service = TelegramAccessService(bot)

    assert await service.check_member(-1001, 101) is expected_member
    assert await service.check_admin(-1001, 101) is expected_admin


@pytest.mark.asyncio
async def test_telegram_access_fails_closed_on_api_error() -> None:
    bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=RuntimeError("Telegram down")))
    service = TelegramAccessService(bot)

    assert await service.check_member(-1001, 101) is False
    assert await service.check_admin(-1001, 101) is False
