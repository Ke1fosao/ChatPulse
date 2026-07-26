from datetime import UTC, datetime

import pytest

from app.database import Database
from app.domain import GroupData, MessageActivity, UserData
from app.repositories.activity import ActivityRepository
from app.repositories.gamification import GamificationRepository
from app.services.activity_writes import ActivityWriteService


@pytest.mark.asyncio
async def test_message_activity_and_xp_roll_back_together(tmp_path, monkeypatch) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'activity-write.db'}")
    await database.create_schema()
    activity = ActivityRepository(database.session_factory)
    gamification = GamificationRepository(database.session_factory)
    service = ActivityWriteService(database.session_factory, activity, gamification)
    await activity.upsert_group(
        GroupData(-1001, "Test", None, "Europe/Kyiv"),
        bot_status="administrator",
        is_active=True,
    )

    async def fail(*_args, **_kwargs):
        raise RuntimeError("xp failed")

    monkeypatch.setattr(gamification, "award_message_xp_in_session", fail)
    with pytest.raises(RuntimeError, match="xp failed"):
        await service.record_message(
            chat_id=-1001,
            user=UserData(101, "dmytro", "Dmytro", None, "uk"),
            activity=MessageActivity(is_media=False, is_reply=False),
            occurred_at=datetime(2026, 7, 26, 10, tzinfo=UTC),
            message_id=1,
        )

    assert await activity.get_member_stats(-1001, 101) is None
    summary = await activity.get_group_summary(-1001, "all")
    assert summary["messages_count"] == 0
    await database.dispose()
