from datetime import UTC, date, datetime, timedelta

import pytest

from app.database import Database
from app.engagement_models import EngagementProfile
from app.models import ChatGroup, GroupMember, User
from app.repositories.engagement import EngagementRepository


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@pytest.mark.asyncio
async def test_onboarding_progresses_from_start_to_first_group_activity(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'engagement.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    async with database.session_factory() as session, session.begin():
        session.add(User(telegram_id=101, first_name="Dima", username="dima"))
        session.add(
            ChatGroup(
                telegram_chat_id=-1001,
                title="ChatPulse Test",
                username="chatpulse_test",
                bot_status="administrator",
                is_active=True,
            )
        )

    repository = EngagementRepository(database.session_factory)
    await repository.mark_private_started(101, now=now)
    started = await repository.get_onboarding(101, bot_username="chatpulse_bot", now=now)
    assert started["completed_steps"] == 1
    assert started["steps"][0]["completed"] is True
    assert started["steps"][1]["completed"] is False
    assert started["add_group_url"].endswith("?startgroup=true")

    await repository.link_group(101, -1001, bot_status="administrator", now=now)
    connected = await repository.get_onboarding(101, bot_username="chatpulse_bot", now=now)
    assert connected["completed_steps"] == 2
    assert connected["steps"][1]["completed"] is True
    assert connected["steps"][2]["completed"] is False

    async with database.session_factory() as session, session.begin():
        session.add(
            GroupMember(
                telegram_chat_id=-1001,
                telegram_user_id=101,
                display_name="Dima",
                username="dima",
                messages_count=1,
                xp_total=5,
                current_streak=1,
                longest_streak=1,
                last_streak_date=date(2026, 7, 23),
                first_seen_at=now,
                last_seen_at=now,
            )
        )

    completed = await repository.get_onboarding(101, bot_username="chatpulse_bot", now=now)
    assert completed["completed_steps"] == 3
    assert completed["is_complete"] is True
    assert all(step["completed"] for step in completed["steps"])

    async with database.session_factory() as session:
        profile = await session.get(EngagementProfile, 101)
        assert profile is not None
        assert profile.onboarding_completed_at is not None
        assert _utc(profile.onboarding_completed_at) == now

    await database.dispose()


@pytest.mark.asyncio
async def test_notification_claims_are_idempotent_and_respect_cooldown(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'engagement-notifications.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 18, 0, tzinfo=UTC)
    async with database.session_factory() as session, session.begin():
        session.add(User(telegram_id=202, first_name="Vika"))

    repository = EngagementRepository(database.session_factory)
    await repository.mark_private_started(202, now=now - timedelta(days=2))

    first = await repository.claim_notification(
        202,
        notification_type="streak_risk",
        notification_key="streak:-200:2026-07-23",
        chat_id=-200,
        now=now,
    )
    assert first is not None
    await repository.mark_notification_sent(first, now=now)

    duplicate = await repository.claim_notification(
        202,
        notification_type="streak_risk",
        notification_key="streak:-200:2026-07-23",
        chat_id=-200,
        now=now,
    )
    assert duplicate is None

    cooldown = await repository.claim_notification(
        202,
        notification_type="achievement_near",
        notification_key="achievement:messages_10",
        now=now + timedelta(hours=2),
    )
    assert cooldown is None

    next_day = await repository.claim_notification(
        202,
        notification_type="achievement_near",
        notification_key="achievement:messages_10",
        now=now + timedelta(hours=21),
    )
    assert next_day is not None
    await database.dispose()


@pytest.mark.asyncio
async def test_rank_snapshot_reports_only_real_improvement(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'rank-snapshot.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    async with database.session_factory() as session, session.begin():
        session.add(User(telegram_id=303, first_name="Ranked"))
        session.add(ChatGroup(telegram_chat_id=-300, title="Rank Group", is_active=True))

    repository = EngagementRepository(database.session_factory)
    first = await repository.update_rank_snapshot(
        303,
        -300,
        rank=5,
        period_start=date(2026, 7, 13),
        now=now,
    )
    improved = await repository.update_rank_snapshot(
        303,
        -300,
        rank=2,
        period_start=date(2026, 7, 20),
        now=now + timedelta(days=7),
    )
    unchanged_period = await repository.update_rank_snapshot(
        303,
        -300,
        rank=1,
        period_start=date(2026, 7, 20),
        now=now + timedelta(days=7, hours=1),
    )

    assert first == {"previous_rank": None, "current_rank": 5, "improved_by": 0}
    assert improved == {"previous_rank": 5, "current_rank": 2, "improved_by": 3}
    assert unchanged_period == {"previous_rank": 2, "current_rank": 1, "improved_by": 0}
    await database.dispose()
