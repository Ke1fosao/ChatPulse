import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.database import Database
from app.domain import GroupData, MessageActivity, UserData
from app.repositories.activity import ActivityRepository
from app.repositories.gamification import GamificationRepository
from app.services.gamification import GLOBAL_DAILY_XP_CAP, GROUP_DAILY_XP_CAP, level_for_xp


async def _register(
    activity: ActivityRepository,
    *,
    message_id: int,
    occurred_at: datetime,
) -> MessageActivity:
    payload = MessageActivity(
        is_media=False,
        is_reply=False,
        content_length=32,
        content_fingerprint=f"fingerprint-{message_id}",
        content_simhash=message_id,
        has_qualifying_text=True,
    )
    await activity.record_message(
        chat_id=-1001,
        user=UserData(101, "dmytro", "Dmytro", None, "uk"),
        activity=payload,
        occurred_at=occurred_at,
        message_id=message_id,
    )
    return payload


@pytest.mark.asyncio
async def test_same_message_receives_xp_at_most_once(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'same-message.db'}")
    await database.create_schema()
    activity = ActivityRepository(database.session_factory)
    repository = GamificationRepository(database.session_factory)
    await activity.upsert_group(
        GroupData(-1001, "Test", None, "Europe/Kyiv"),
        bot_status="administrator",
        is_active=True,
    )
    occurred = datetime(2026, 7, 26, 10, tzinfo=UTC)
    payload = await _register(activity, message_id=1, occurred_at=occurred)

    updates = await asyncio.gather(
        *[
            repository.award_message_xp(
                chat_id=-1001,
                user_id=101,
                message_id=1,
                activity=payload,
                occurred_at=occurred,
            )
            for _ in range(20)
        ]
    )
    assert sum(update.group_xp_awarded > 0 for update in updates) == 1
    profile = await repository.get_profile(-1001, 101)
    assert profile is not None
    assert profile["group_xp_total"] == sum(update.group_xp_awarded for update in updates)
    await database.dispose()


@pytest.mark.asyncio
async def test_parallel_reaction_awards_respect_caps_and_levels(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'reaction-cap.db'}")
    await database.create_schema()
    activity = ActivityRepository(database.session_factory)
    repository = GamificationRepository(database.session_factory)
    await activity.upsert_group(
        GroupData(-1001, "Test", None, "Europe/Kyiv"),
        bot_status="administrator",
        is_active=True,
    )
    occurred = datetime(2026, 7, 26, 10, tzinfo=UTC)
    await _register(activity, message_id=1, occurred_at=occurred)

    updates = await asyncio.gather(
        *[
            repository.award_reaction_xp(
                chat_id=-1001,
                message_id=1,
                positive_delta=4,
                occurred_at=occurred + timedelta(seconds=index),
            )
            for index in range(60)
        ]
    )
    profile = await repository.get_profile(-1001, 101)
    assert profile is not None
    awarded = sum(update.group_xp_awarded for update in updates)
    assert profile["group_xp_total"] == awarded == GROUP_DAILY_XP_CAP
    assert profile["global_xp_total"] <= GLOBAL_DAILY_XP_CAP
    assert profile["group_level"] == level_for_xp(profile["group_xp_total"])
    assert profile["global_level"] == level_for_xp(profile["global_xp_total"])
    await database.dispose()
