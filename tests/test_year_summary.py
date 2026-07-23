from datetime import UTC, date, datetime

import pytest

from app.database import Database
from app.models import ChatGroup, DailyActivity, GroupMember, User
from app.repositories.miniapp_v2 import AchievementMiniAppRepository


@pytest.fixture
async def year_summary_repository(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'year-summary.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(telegram_id=909, first_name="Year", global_xp_total=120, last_activity_at=now),
                ChatGroup(telegram_chat_id=-909, title="Year Group", is_active=True),
                GroupMember(
                    telegram_chat_id=-909,
                    telegram_user_id=909,
                    display_name="Year",
                    current_streak=4,
                    longest_streak=12,
                    first_seen_at=now,
                    last_seen_at=now,
                ),
                DailyActivity(
                    telegram_chat_id=-909,
                    telegram_user_id=909,
                    activity_date=date(2026, 1, 10),
                    messages_count=15,
                    xp_earned=30,
                ),
                DailyActivity(
                    telegram_chat_id=-909,
                    telegram_user_id=909,
                    activity_date=date(2026, 7, 20),
                    messages_count=25,
                    xp_earned=70,
                ),
            ]
        )
    yield AchievementMiniAppRepository(database.session_factory)
    await database.dispose()


@pytest.mark.asyncio
async def test_builds_private_year_summary(year_summary_repository) -> None:
    summary = await year_summary_repository.get_year_summary(909, 2026)

    assert summary is not None
    assert summary["year"] == 2026
    assert summary["messages_count"] == 40
    assert summary["xp_earned"] == 100
    assert summary["active_days"] == 2
    assert summary["groups_count"] == 1
    assert summary["best_streak"] == 12
    assert summary["top_month"] == 7
