from datetime import UTC, datetime

import pytest

from app.database import Database
from app.domain import GroupData, MessageActivity, UserData
from app.repositories.activity import ActivityRepository
from app.repositories.gamification import GamificationRepository
from app.services.gamification import content_fingerprints


@pytest.fixture
async def repositories(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'gamification.db'}")
    await database.create_schema()
    activity = ActivityRepository(database.session_factory)
    gamification = GamificationRepository(database.session_factory)
    yield activity, gamification
    await database.dispose()


async def register_message(
    activity: ActivityRepository,
    *,
    chat_id: int,
    message_id: int,
    user_id: int = 101,
    occurred_at: datetime,
    username: str | None = None,
) -> MessageActivity:
    await activity.upsert_group(
        GroupData(chat_id, f"Group {chat_id}", username, "Europe/Kyiv"),
        bot_status="member",
        is_active=True,
    )
    fingerprint, simhash, length, qualifies = content_fingerprints(
        f"message {message_id}",
        media_key=None,
        secret="test-secret",
    )
    message_activity = MessageActivity(
        is_media=False,
        is_reply=False,
        content_length=length,
        content_fingerprint=fingerprint,
        content_simhash=simhash,
        has_qualifying_text=qualifies,
    )
    await activity.record_message(
        chat_id=chat_id,
        user=UserData(user_id, "dmytro", "Dmytro", None, "uk"),
        activity=message_activity,
        occurred_at=occurred_at,
        message_id=message_id,
    )
    return message_activity


@pytest.mark.asyncio
async def test_group_and_global_daily_caps(repositories) -> None:
    activity, gamification = repositories
    occurred = datetime(2026, 7, 22, 10, tzinfo=UTC)

    for index, chat_id in enumerate((-1001, -1002, -1003), start=1):
        await register_message(
            activity,
            chat_id=chat_id,
            message_id=index,
            occurred_at=occurred,
        )
        await gamification.award_reaction_xp(
            chat_id=chat_id,
            message_id=index,
            positive_delta=100,
            occurred_at=occurred,
        )

    first = await gamification.get_profile(-1001, 101)
    third = await gamification.get_profile(-1003, 101)
    assert first is not None and third is not None
    assert first["group_xp_total"] == 200
    assert third["group_xp_total"] == 200
    assert third["global_xp_total"] == 400


@pytest.mark.asyncio
async def test_three_monthly_protection_days_keep_streak(repositories) -> None:
    activity, gamification = repositories
    first_day = datetime(2026, 7, 1, 10, tzinfo=UTC)
    await register_message(
        activity,
        chat_id=-1001,
        message_id=1,
        occurred_at=first_day,
    )

    for occurred in (first_day, datetime(2026, 7, 5, 10, tzinfo=UTC)):
        update = await gamification.award_reaction_xp(
            chat_id=-1001,
            message_id=1,
            positive_delta=4,
            occurred_at=occurred,
        )
    assert update.current_streak == 2

    reset = await gamification.award_reaction_xp(
        chat_id=-1001,
        message_id=1,
        positive_delta=4,
        occurred_at=datetime(2026, 7, 10, 10, tzinfo=UTC),
    )
    assert reset.current_streak == 1
    profile = await gamification.get_profile(-1001, 101)
    assert profile is not None
    assert profile["protection_left"] == 0


@pytest.mark.asyncio
async def test_achievement_is_persisted_once(repositories) -> None:
    activity, gamification = repositories
    occurred = datetime(2026, 7, 22, 10, tzinfo=UTC)
    await register_message(
        activity,
        chat_id=-1001,
        message_id=1,
        occurred_at=occurred,
    )
    first = await gamification.award_reaction_xp(
        chat_id=-1001,
        message_id=1,
        positive_delta=4,
        occurred_at=occurred,
    )
    second = await gamification.award_reaction_xp(
        chat_id=-1001,
        message_id=1,
        positive_delta=1,
        occurred_at=occurred,
    )
    assert [item.code for item in first.achievements] == ["first_steps"]
    assert second.achievements == ()


@pytest.mark.asyncio
async def test_top_message_uses_reaction_total_and_link(repositories) -> None:
    activity, gamification = repositories
    occurred = datetime(2026, 7, 22, 10, tzinfo=UTC)
    await register_message(
        activity,
        chat_id=-1001234567890,
        message_id=11,
        occurred_at=occurred,
    )
    await register_message(
        activity,
        chat_id=-1001234567890,
        message_id=12,
        occurred_at=occurred,
    )
    await gamification.update_message_reaction_total(-1001234567890, 11, total=3)
    await gamification.update_message_reaction_total(-1001234567890, 12, total=8)

    top = await gamification.get_top_message(-1001234567890, now=occurred)
    assert top is not None
    assert top["message_id"] == 12
    assert top["reactions_count"] == 8
    assert top["url"] == "https://t.me/c/1234567890/12"
