from datetime import UTC, date, datetime

import pytest

from app.database import Database
from app.models import ChatGroup, DailyActivity, GroupMember, User
from app.repositories.miniapp_v2 import AchievementMiniAppRepository


@pytest.fixture
async def premium_analytics_repository(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'premium-analytics.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(telegram_id=501, first_name="Premium", last_activity_at=now),
                ChatGroup(
                    telegram_chat_id=-5001,
                    title="Premium Group",
                    is_active=True,
                    timezone="Europe/Kyiv",
                ),
                GroupMember(
                    telegram_chat_id=-5001,
                    telegram_user_id=501,
                    display_name="Premium",
                    first_seen_at=now,
                    last_seen_at=now,
                ),
                DailyActivity(
                    telegram_chat_id=-5001,
                    telegram_user_id=501,
                    activity_date=date(2026, 7, 23),
                    messages_count=20,
                    reactions_received=6,
                    replies_count=4,
                    media_count=3,
                    xp_earned=42,
                ),
                DailyActivity(
                    telegram_chat_id=-5001,
                    telegram_user_id=501,
                    activity_date=date(2026, 5, 1),
                    messages_count=8,
                    reactions_received=2,
                    replies_count=1,
                    media_count=1,
                    xp_earned=14,
                ),
                DailyActivity(
                    telegram_chat_id=-5001,
                    telegram_user_id=501,
                    activity_date=date(2026, 3, 1),
                    messages_count=5,
                    reactions_received=1,
                    replies_count=1,
                    xp_earned=9,
                ),
            ]
        )
    yield AchievementMiniAppRepository(database.session_factory)
    await database.dispose()


@pytest.mark.asyncio
async def test_returns_validated_quarter_half_year_and_year_analytics(
    premium_analytics_repository,
) -> None:
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)

    quarter = await premium_analytics_repository.get_premium_analytics(
        501,
        -5001,
        "quarter",
        compare="half_year",
        now=now,
    )

    assert quarter is not None
    assert quarter["period"] == "quarter"
    assert quarter["days"] == 90
    assert quarter["overview"]["messages_count"] == 28
    assert quarter["comparison"]["period"] == "half_year"
    assert quarter["comparison"]["overview"]["messages_count"] == 33
    assert quarter["trends"]["messages_count"] < 0
    assert len(quarter["activity_series"]) == 2


@pytest.mark.asyncio
async def test_premium_analytics_requires_group_membership(premium_analytics_repository) -> None:
    assert (
        await premium_analytics_repository.get_premium_analytics(
            999,
            -5001,
            "year",
        )
        is None
    )
