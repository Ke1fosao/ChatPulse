from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.weekly_reports import send_due_weekly_reports


@pytest.mark.asyncio
async def test_weekly_report_is_sent_and_marked() -> None:
    repository = SimpleNamespace(
        list_due_weekly_reports=AsyncMock(
            return_value=[{"telegram_chat_id": -1001, "title": "Test"}]
        ),
        get_group_summary=AsyncMock(
            return_value={
                "messages_count": 5,
                "media_count": 1,
                "replies_count": 2,
                "reactions_received": 3,
                "photo_count": 1,
                "voice_count": 0,
                "night_messages_count": 1,
                "morning_messages_count": 0,
                "active_members": 1,
            }
        ),
        get_period_members=AsyncMock(
            return_value=[
                {
                    "telegram_user_id": 1,
                    "display_name": "Dmytro",
                    "username": None,
                    "messages_count": 5,
                    "media_count": 1,
                    "replies_count": 2,
                    "reactions_received": 3,
                    "photo_count": 1,
                    "voice_count": 0,
                    "night_messages_count": 1,
                    "morning_messages_count": 0,
                }
            ]
        ),
        get_popular_reaction=AsyncMock(return_value=("❤️", 3)),
        mark_weekly_report_sent=AsyncMock(),
    )
    bot = SimpleNamespace(send_message=AsyncMock())

    sent = await send_due_weekly_reports(bot, repository)

    assert sent == 1
    bot.send_message.assert_awaited_once()
    repository.mark_weekly_report_sent.assert_awaited_once()
