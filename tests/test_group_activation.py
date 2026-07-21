from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message

from app.bot.routers.groups import activate_group


def make_message() -> Message:
    return Message.model_validate(
        {
            "message_id": 1,
            "date": datetime(2026, 7, 21, 19, 0, tzinfo=UTC),
            "chat": {"id": -1001, "type": "supergroup", "title": "Test group"},
            "from": {"id": 101, "is_bot": False, "first_name": "Dmytro"},
            "text": "/activate",
        }
    )


@pytest.mark.asyncio
async def test_activate_group_marks_admin_group_active() -> None:
    repository = SimpleNamespace(upsert_group=AsyncMock())
    bot = SimpleNamespace(
        id=999,
        get_chat_member=AsyncMock(
            return_value=SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR)
        ),
    )

    active = await activate_group(
        make_message(),
        repository=repository,
        bot=bot,
        default_timezone="Europe/Kyiv",
    )

    assert active is True
    repository.upsert_group.assert_awaited_once()
    assert repository.upsert_group.await_args.kwargs == {
        "bot_status": "administrator",
        "is_active": True,
    }
