from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.weekly_reports import send_due_weekly_reports, send_weekly_report


def legacy_repository():
    return SimpleNamespace(
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


@pytest.mark.asyncio
async def test_weekly_report_is_sent_and_marked() -> None:
    repository = legacy_repository()
    bot = SimpleNamespace(send_message=AsyncMock())

    sent = await send_due_weekly_reports(bot, repository)

    assert sent == 1
    bot.send_message.assert_awaited_once()
    repository.mark_weekly_report_sent.assert_awaited_once()


@pytest.mark.asyncio
async def test_single_manual_report_can_skip_schedule_marker() -> None:
    repository = legacy_repository()
    bot = SimpleNamespace(send_message=AsyncMock())

    delivered = await send_weekly_report(
        bot,
        repository,
        -1001,
        mark_sent=False,
    )

    assert delivered is True
    bot.send_message.assert_awaited_once()
    repository.mark_weekly_report_sent.assert_not_awaited()
