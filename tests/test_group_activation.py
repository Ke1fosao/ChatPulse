from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
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
async def test_first_group_message_activates_group_and_is_recorded() -> None:
    repository = SimpleNamespace(
        upsert_group=AsyncMock(),
        record_message=AsyncMock(return_value=True),
    )

    await track_group_message(
        make_message(),
        repository=repository,
        default_timezone="Europe/Kyiv",
    )

    repository.upsert_group.assert_awaited_once()
    assert repository.upsert_group.await_args.kwargs == {
        "bot_status": "member",
        "is_active": True,
    }
    repository.record_message.assert_awaited_once()
