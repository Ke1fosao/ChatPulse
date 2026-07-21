from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message

from app.bot.routers.groups import track_group_message


def make_message() -> Message:
    return Message.model_validate(
        {
            "message_id": 1,
            "date": datetime(2026, 7, 21, 19, 0, tzinfo=UTC),
            "chat": {"id": -1001, "type": "supergroup", "title": "Test group"},
            "from": {"id": 101, "is_bot": False, "first_name": "Dmytro"},
            "text": "hello",
        }
    )


@pytest.mark.asyncio
async def test_inactive_group_is_rechecked_and_message_is_retried() -> None:
    repository = SimpleNamespace(
        record_message=AsyncMock(side_effect=[False, True]),
        upsert_group=AsyncMock(),
    )
    bot = SimpleNamespace(
        id=999,
        get_chat_member=AsyncMock(
            return_value=SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR)
        ),
    )

    await track_group_message(
        make_message(),
        repository=repository,
        bot=bot,
        default_timezone="Europe/Kyiv",
    )

    assert repository.record_message.await_count == 2
    repository.upsert_group.assert_awaited_once()
