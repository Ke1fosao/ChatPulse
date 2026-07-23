from datetime import UTC, date, datetime, timedelta

import pytest

from app.database import Database
from app.engagement_models import EngagementRankSnapshot
from app.models import ChatGroup, DailyActivity, GroupMember, MemberAchievement, User
from app.repositories.groups_v2 import GroupsV2Repository


@pytest.fixture
async def groups_v2_repository(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'groups-v2.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(telegram_id=101, first_name="Dmytro", username="dmytro"),
                User(telegram_id=202, first_name="Vika", username="vika"),
                ChatGroup(
                    telegram_chat_id=-1001,
                    title="Active Group",
                    username="active_group",
                    bot_status="administrator",
                    is_active=True,
                    timezone="UTC",
                ),
                ChatGroup(
                    telegram_chat_id=-2002,
                    title="Paused Group",
                    bot_status="administrator",
                    is_active=True,
                    is_paused=True,
                    timezone="UTC",
                ),
                ChatGroup(
                    telegram_chat_id=-3003,
                    title="Needs Setup",
                    bot_status="member",
                    is_active=False,
                    timezone="UTC",
                ),
                GroupMember(
                    telegram_chat_id=-1001,
                    telegram_user_id=101,
                    display_name="Dmytro",
                    username="dmytro",
                    messages_count=50,
                    reactions_received=18,
                    replies_count=10,
                    xp_total=400,
                    level=4,
                    current_streak=5,
                    longest_streak=8,
                    first_seen_at=now - timedelta(days=20),
                    last_seen_at=now - timedelta(hours=2),
                ),
                GroupMember(
                    telegram_chat_id=-1001,
                    telegram_user_id=202,
                    display_name="Vika",
                    username="vika",
                    messages_count=80,
                    reactions_received=25,
                    replies_count=14,
                    xp_total=700,
                    level=5,
                    current_streak=4,
                    longest_streak=7,
                    first_seen_at=now - timedelta(days=20),
                    last_seen_at=now - timedelta(hours=1),
                ),
                GroupMember(
                    telegram_chat_id=-2002,
                    telegram_user_id=101,
                    display_name="Dmytro",
                    first_seen_at=now - timedelta(days=20),
                    last_seen_at=now - timedelta(days=2),
                ),
                GroupMember(
                    telegram_chat_id=-3003,
                    telegram_user_id=101,
                    display_name="Dmytro",
                    first_seen_at=now - timedelta(days=20),
                    last_seen_at=now - timedelta(days=10),
                ),
                DailyActivity(
                    telegram_chat_id=-1001,
                    telegram_user_id=101,
                    activity_date=date(2026, 7, 23),
                    messages_count=12,
                    reactions_received=5,
                    replies_count=3,
                    xp_earned=30,
                ),
                DailyActivity(
                    telegram_chat_id=-1001,
                    telegram_user_id=202,
                    activity_date=date(2026, 7, 23),
                    messages_count=18,
                    reactions_received=8,
                    replies_count=4,
                    xp_earned=45,
                ),
                DailyActivity(
                    telegram_chat_id=-1001,
                    telegram_user_id=101,
                    activity_date=date(2026, 7, 22),
                    messages_count=8,
                    reactions_received=2,
                    replies_count=2,
                    xp_earned=20,
                ),
                DailyActivity(
                    telegram_chat_id=-1001,
                    telegram_user_id=101,
                    activity_date=date(2026, 7, 16),
                    messages_count=5,
                    reactions_received=1,
                    replies_count=0,
                    xp_earned=10,
                ),
                MemberAchievement(
                    telegram_chat_id=-1001,
                    telegram_user_id=101,
                    achievement_code="first_steps",
                    earned_at=now - timedelta(hours=3),
                ),
                EngagementRankSnapshot(
                    telegram_chat_id=-1001,
                    telegram_user_id=101,
                    rank=3,
                    period_start=date(2026, 7, 14),
                    updated_at=now - timedelta(days=7),
                ),
            ]
        )
    yield GroupsV2Repository(database.session_factory)
    await database.dispose()


@pytest.mark.asyncio
async def test_list_groups_enriches_status_and_private_favorites(groups_v2_repository) -> None:
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)

    before = await groups_v2_repository.list_groups(101, now=now)
    assert {item["telegram_chat_id"] for item in before} == {-1001, -2002, -3003}
    by_id = {item["telegram_chat_id"]: item for item in before}
    assert by_id[-1001]["status"]["id"] == "active"
    assert by_id[-1001]["messages_today"] == 30
    assert by_id[-2002]["status"]["id"] == "needs_setup"
    assert by_id[-3003]["attention_reason"]

    await groups_v2_repository.set_favorite(101, -1001, True, now=now)
    after = await groups_v2_repository.list_groups(101, now=now)
    assert next(item for item in after if item["telegram_chat_id"] == -1001)["is_favorite"]

    other_user = await groups_v2_repository.list_groups(202, now=now)
    assert other_user[0]["is_favorite"] is False


@pytest.mark.asyncio
async def test_favorite_rejects_unknown_membership(groups_v2_repository) -> None:
    with pytest.raises(LookupError):
        await groups_v2_repository.set_favorite(202, -2002, True)


@pytest.mark.asyncio
async def test_overview_returns_pulse_and_privacy_safe_insights(groups_v2_repository) -> None:
    overview = await groups_v2_repository.get_overview(
        101,
        -1001,
        "week",
        now=datetime(2026, 7, 23, 12, 0, tzinfo=UTC),
    )

    assert overview is not None
    assert 0 <= overview["pulse"]["score"] <= 100
    assert overview["group"]["status"]["id"] == "active"
    assert overview["personal_progress"]["rank_change"] == 1
    assert len(overview["top_participants"]) == 2
    assert all("message_text" not in item for item in overview["insights"])


@pytest.mark.asyncio
async def test_split_payloads_and_membership_boundaries(groups_v2_repository) -> None:
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    ranking = await groups_v2_repository.get_ranking(101, -1001, "xp", "week", now=now)
    analytics = await groups_v2_repository.get_analytics(101, -1001, "week", now=now)
    awards = await groups_v2_repository.get_awards(101, -1001, "week", now=now)

    assert ranking is not None and ranking["rows"][0]["rank"] == 1
    assert analytics is not None and "activity_series" in analytics
    assert awards is not None and "nominations" in awards
    assert await groups_v2_repository.get_overview(202, -2002, "week", now=now) is None
