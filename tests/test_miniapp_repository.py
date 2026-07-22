from datetime import UTC, date, datetime

import pytest

from app.database import Database
from app.models import (
    ChatGroup,
    DailyActivity,
    GlobalDailyXP,
    GroupMember,
    MemberAchievement,
    User,
)
from app.repositories.miniapp import MiniAppRepository


@pytest.fixture
async def miniapp_repository(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'miniapp.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 22, 9, 0, tzinfo=UTC)
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(
                    telegram_id=101,
                    username="dmytro",
                    first_name="Dmytro",
                    global_xp_total=850,
                    global_level=4,
                    created_at=now,
                    updated_at=now,
                    last_activity_at=now,
                ),
                User(
                    telegram_id=202,
                    username="vika",
                    first_name="Vika",
                    global_xp_total=1200,
                    global_level=5,
                    created_at=now,
                    updated_at=now,
                    last_activity_at=now,
                ),
                ChatGroup(
                    telegram_chat_id=-1001,
                    title="ChatPulse Test",
                    username="chatpulse_test",
                    is_active=True,
                    timezone="Europe/Kyiv",
                ),
                ChatGroup(
                    telegram_chat_id=-2002,
                    title="Hidden Group",
                    is_active=True,
                    timezone="Europe/Kyiv",
                ),
                GroupMember(
                    telegram_chat_id=-1001,
                    telegram_user_id=101,
                    display_name="Dmytro",
                    username="dmytro",
                    messages_count=42,
                    replies_count=8,
                    reactions_received=15,
                    xp_total=620,
                    level=4,
                    current_streak=6,
                    longest_streak=12,
                    first_seen_at=now,
                    last_seen_at=now,
                ),
                GroupMember(
                    telegram_chat_id=-1001,
                    telegram_user_id=202,
                    display_name="Vika",
                    username="vika",
                    messages_count=60,
                    replies_count=11,
                    reactions_received=22,
                    xp_total=900,
                    level=4,
                    current_streak=4,
                    longest_streak=9,
                    first_seen_at=now,
                    last_seen_at=now,
                ),
                GroupMember(
                    telegram_chat_id=-2002,
                    telegram_user_id=202,
                    display_name="Vika",
                    username="vika",
                    xp_total=300,
                    level=3,
                    first_seen_at=now,
                    last_seen_at=now,
                ),
                DailyActivity(
                    telegram_chat_id=-1001,
                    telegram_user_id=101,
                    activity_date=date(2026, 7, 22),
                    messages_count=7,
                    replies_count=2,
                    reactions_received=3,
                    xp_earned=18,
                ),
                DailyActivity(
                    telegram_chat_id=-1001,
                    telegram_user_id=202,
                    activity_date=date(2026, 7, 22),
                    messages_count=10,
                    replies_count=3,
                    reactions_received=5,
                    xp_earned=25,
                ),
                DailyActivity(
                    telegram_chat_id=-1001,
                    telegram_user_id=101,
                    activity_date=date(2026, 7, 15),
                    messages_count=2,
                    replies_count=0,
                    reactions_received=1,
                    xp_earned=4,
                ),
                GlobalDailyXP(
                    telegram_user_id=101,
                    activity_date=date(2026, 7, 22),
                    xp_earned=18,
                ),
                MemberAchievement(
                    telegram_chat_id=-1001,
                    telegram_user_id=101,
                    achievement_code="first_steps",
                    earned_at=now,
                ),
            ]
        )
    yield MiniAppRepository(database.session_factory)
    await database.dispose()


@pytest.mark.asyncio
async def test_home_contains_global_profile_and_only_users_groups(miniapp_repository) -> None:
    now = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)

    home = await miniapp_repository.get_home(101, now=now)

    assert home is not None
    assert home["user"]["telegram_id"] == 101
    assert home["global_progress"]["xp_total"] == 850
    assert home["global_progress"]["rank"] == 2
    assert home["quick_stats"]["xp_today"] == 18
    assert [group["telegram_chat_id"] for group in home["groups"]] == [-1001]
    assert home["recent_achievements"][0]["code"] == "first_steps"


@pytest.mark.asyncio
async def test_group_dashboard_compares_periods_and_returns_private_safe_data(
    miniapp_repository,
) -> None:
    now = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)

    dashboard = await miniapp_repository.get_group_dashboard(101, -1001, "week", now=now)

    assert dashboard is not None
    assert dashboard["group"]["title"] == "ChatPulse Test"
    assert dashboard["overview"]["current"]["messages_count"] == 17
    assert dashboard["overview"]["previous"]["messages_count"] == 2
    assert dashboard["personal_progress"]["xp_total"] == 620
    assert dashboard["leaderboard"][0]["telegram_user_id"] == 202
    assert "message_text" not in dashboard


@pytest.mark.asyncio
async def test_repository_does_not_expose_group_without_membership(miniapp_repository) -> None:
    assert await miniapp_repository.get_group_dashboard(101, -2002, "week") is None
    assert await miniapp_repository.get_rankings(101, -2002, "xp", "week") is None
