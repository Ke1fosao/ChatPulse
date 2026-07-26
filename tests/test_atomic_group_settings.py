from datetime import UTC, datetime

import pytest

from app.database import Database
from app.domain import GroupData, MessageActivity, UserData
from app.repositories.activity import ActivityRepository
from app.services.group_settings import GroupSettingsService


@pytest.mark.asyncio
async def test_group_settings_update_rolls_back_all_fields(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'settings.db'}")
    await database.create_schema()
    repository = ActivityRepository(database.session_factory)
    await repository.upsert_group(
        GroupData(-1001, "Test", None, "Europe/Kyiv"),
        bot_status="administrator",
        is_active=True,
    )

    async def fail(name, _session):
        if name == "extras_updated":
            raise RuntimeError("stop")

    service = GroupSettingsService(database.session_factory, checkpoint=fail)
    with pytest.raises(RuntimeError, match="stop"):
        await service.update_settings(
            actor_user_id=101,
            chat_id=-1001,
            values={
                "report_time": "21:45",
                "report_card_theme": "telegram_wave",
                "track_media": False,
            },
        )

    settings = await repository.get_group_settings(-1001)
    assert settings is not None
    assert settings["report_hour"] == 20
    assert settings["report_minute"] == 0
    assert settings["track_media"] is True
    await database.dispose()


@pytest.mark.asyncio
async def test_group_reset_rolls_back_deletions(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'reset.db'}")
    await database.create_schema()
    repository = ActivityRepository(database.session_factory)
    await repository.upsert_group(
        GroupData(-1001, "Test", None, "Europe/Kyiv"),
        bot_status="administrator",
        is_active=True,
    )
    await repository.record_message(
        chat_id=-1001,
        user=UserData(101, "dmytro", "Dmytro", None, "uk"),
        activity=MessageActivity(is_media=False, is_reply=False),
        occurred_at=datetime(2026, 7, 26, 10, tzinfo=UTC),
        message_id=1,
    )

    async def fail(name, _session):
        if name == "activity_deleted":
            raise RuntimeError("stop")

    service = GroupSettingsService(database.session_factory, checkpoint=fail)
    with pytest.raises(RuntimeError, match="stop"):
        await service.reset_group(actor_user_id=101, chat_id=-1001)

    member = await repository.get_member_stats(-1001, 101)
    assert member is not None
    assert member["messages_count"] == 1
    await database.dispose()
