from datetime import UTC, datetime

import pytest

from app.database import Database
from app.domain import GroupData, MessageActivity, UserData
from app.repositories.achievements import AchievementRepository
from app.repositories.activity import ActivityRepository
from app.repositories.gamification_v2 import AchievementGamificationRepository
from app.services.gamification import content_fingerprints


@pytest.mark.asyncio
async def test_unlock_creates_one_durable_celebration_event(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'achievement-v2.db'}")
    await database.create_schema()
    activity_repository = ActivityRepository(database.session_factory)
    gamification_repository = AchievementGamificationRepository(database.session_factory)
    achievement_repository = AchievementRepository(database.session_factory)
    occurred_at = datetime(2026, 7, 22, 10, tzinfo=UTC)

    await activity_repository.upsert_group(
        GroupData(-1001, "ChatPulse Team", None, "Europe/Kyiv"),
        bot_status="member",
        is_active=True,
    )
    fingerprint, simhash, length, qualifies = content_fingerprints(
        "achievement event message",
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
    await activity_repository.record_message(
        chat_id=-1001,
        user=UserData(101, "dmytro", "Dmytro", None, "uk"),
        activity=message_activity,
        occurred_at=occurred_at,
        message_id=1,
    )

    first = await gamification_repository.award_reaction_xp(
        chat_id=-1001,
        message_id=1,
        positive_delta=4,
        occurred_at=occurred_at,
    )
    second = await gamification_repository.award_reaction_xp(
        chat_id=-1001,
        message_id=1,
        positive_delta=1,
        occurred_at=occurred_at,
    )

    assert "first_steps" in {item.code for item in first.achievements}
    assert "first_steps" not in {item.code for item in second.achievements}

    pending = await achievement_repository.list_pending_events(101)
    first_steps = [item for item in pending if item["achievement"]["code"] == "first_steps"]
    assert len(first_steps) == 1
    assert first_steps[0]["achievement"]["rarity"] == "common"

    event_id = first_steps[0]["event_id"]
    assert await achievement_repository.mark_seen(101, event_id) is True
    assert await achievement_repository.mark_seen(999, event_id) is False
    assert all(
        item["event_id"] != event_id
        for item in await achievement_repository.list_pending_events(101)
    )

    await database.dispose()
