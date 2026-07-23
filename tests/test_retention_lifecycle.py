from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.database import Database
from app.models import ChatGroup, GroupMember, User
from app.repositories.engagement import EngagementRepository
from app.services.retention_lifecycle import RetentionLifecycleService


async def _started_user(
    database: Database,
    *,
    user_id: int,
    chat_id: int,
    messages: int,
    streak: int,
    last_streak_date: date | None,
    now: datetime,
) -> None:
    async with database.session_factory() as session, session.begin():
        session.add(User(telegram_id=user_id, first_name=f"User {user_id}"))
        session.add(
            ChatGroup(
                telegram_chat_id=chat_id,
                title=f"Group {chat_id}",
                timezone="Europe/Kyiv",
                bot_status="administrator",
                is_active=True,
            )
        )
        session.add(
            GroupMember(
                telegram_chat_id=chat_id,
                telegram_user_id=user_id,
                display_name=f"User {user_id}",
                messages_count=messages,
                xp_total=messages * 5,
                current_streak=streak,
                longest_streak=streak,
                last_streak_date=last_streak_date,
                first_seen_at=now - timedelta(days=5),
                last_seen_at=now - timedelta(days=1),
            )
        )
    await EngagementRepository(database.session_factory).mark_private_started(
        user_id,
        now=now - timedelta(days=5),
    )


def _service(database: Database) -> RetentionLifecycleService:
    return RetentionLifecycleService(
        database.session_factory,
        miniapp_url="https://example.com/miniapp",
    )


@pytest.mark.asyncio
async def test_sends_streak_risk_once_after_19_local_time(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'retention-streak.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 17, 30, tzinfo=UTC)  # 20:30 in Kyiv
    await _started_user(
        database,
        user_id=401,
        chat_id=-401,
        messages=20,
        streak=4,
        last_streak_date=date(2026, 7, 22),
        now=now,
    )

    bot = AsyncMock()
    service = _service(database)
    first = await service.send_due(bot, now=now)
    second = await service.send_due(bot, now=now + timedelta(minutes=5))

    assert first["streak_sent"] == 1
    assert second["streak_sent"] == 0
    bot.send_message.assert_awaited_once()
    sent_text = bot.send_message.await_args.args[1]
    assert "Серія" in sent_text
    assert "4" in sent_text
    await database.dispose()


@pytest.mark.asyncio
async def test_sends_near_achievement_when_no_streak_warning_is_due(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'retention-achievement.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    await _started_user(
        database,
        user_id=402,
        chat_id=-402,
        messages=9,
        streak=0,
        last_streak_date=None,
        now=now,
    )

    bot = AsyncMock()
    service = _service(database)
    result = await service.send_due(bot, now=now)

    assert result["achievement_sent"] == 1
    sent_text = bot.send_message.await_args.args[1]
    assert "досягнення" in sent_text.lower()
    assert "1" in sent_text
    await database.dispose()


@pytest.mark.asyncio
async def test_weekly_report_notification_includes_rank_improvement_and_is_idempotent(
    tmp_path,
) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'retention-weekly.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    await _started_user(
        database,
        user_id=403,
        chat_id=-403,
        messages=100,
        streak=3,
        last_streak_date=date(2026, 7, 23),
        now=now,
    )
    repository = EngagementRepository(database.session_factory)
    await repository.update_rank_snapshot(
        403,
        -403,
        rank=4,
        period_start=date(2026, 7, 13),
        now=now - timedelta(days=7),
    )

    bot = AsyncMock()
    service = _service(database)
    first = await service.notify_weekly_report(
        bot,
        chat_id=-403,
        group_title="Weekly Group",
        report_key="2026-07-20",
        ranks={403: 2},
        now=now,
    )
    second = await service.notify_weekly_report(
        bot,
        chat_id=-403,
        group_title="Weekly Group",
        report_key="2026-07-20",
        ranks={403: 2},
        now=now,
    )

    assert first == 1
    assert second == 0
    assert "2 місця" in bot.send_message.await_args.args[1]
    await database.dispose()
