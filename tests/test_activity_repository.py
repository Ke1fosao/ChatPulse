from datetime import UTC, datetime

import pytest

from app.database import Database
from app.domain import GroupData, MessageActivity, UserData
from app.repositories.activity import ActivityRepository


@pytest.fixture
async def repository(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await database.create_schema()
    yield ActivityRepository(database.session_factory)
    await database.dispose()


async def active_group(repository: ActivityRepository, timezone: str = "Europe/Kyiv") -> None:
    await repository.upsert_group(
        GroupData(-1001, "Test group", None, timezone),
        bot_status="member",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_message_is_counted_in_local_day_and_periods(repository: ActivityRepository) -> None:
    await active_group(repository)
    user = UserData(101, "dmytro", "Dmytro", None, "uk")
    await repository.record_message(
        chat_id=-1001,
        user=user,
        activity=MessageActivity(True, True, is_photo=True),
        occurred_at=datetime(2026, 7, 20, 22, 30, tzinfo=UTC),
        message_id=50,
    )

    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    today = await repository.get_group_summary(-1001, "today", now=now)
    week = await repository.get_group_summary(-1001, "week", now=now)

    assert today["messages_count"] == 1
    assert today["photo_count"] == 1
    assert today["night_messages_count"] == 1
    assert week["replies_count"] == 1


@pytest.mark.asyncio
async def test_paused_group_does_not_record(repository: ActivityRepository) -> None:
    await active_group(repository)
    await repository.update_group_setting(-1001, "is_paused", True)
    recorded = await repository.record_message(
        chat_id=-1001,
        user=UserData(101, None, "Dmytro", None, "uk"),
        activity=MessageActivity(False, False),
        occurred_at=datetime.now(UTC),
        message_id=1,
    )
    assert recorded is False


@pytest.mark.asyncio
async def test_reaction_updates_author_and_popular_emoji(repository: ActivityRepository) -> None:
    await active_group(repository)
    user = UserData(101, None, "Dmytro", None, "uk")
    occurred = datetime(2026, 7, 21, 10, tzinfo=UTC)
    await repository.record_message(
        chat_id=-1001,
        user=user,
        activity=MessageActivity(False, False),
        occurred_at=occurred,
        message_id=55,
    )
    assert await repository.record_reaction(
        chat_id=-1001,
        message_id=55,
        old_reactions=[],
        new_reactions=["❤️"],
        occurred_at=occurred,
    )
    member = await repository.get_member_stats(-1001, 101, "today", now=occurred)
    assert member is not None
    assert member["reactions_received"] == 1
    assert await repository.get_popular_reaction(-1001, "today", now=occurred) == ("❤️", 1)


@pytest.mark.asyncio
async def test_claim_update_rejects_duplicate(repository: ActivityRepository) -> None:
    assert await repository.claim_update(123, "message") is True
    assert await repository.claim_update(123, "message") is False


@pytest.mark.asyncio
async def test_reset_removes_activity_but_keeps_settings(repository: ActivityRepository) -> None:
    await active_group(repository)
    await repository.update_group_setting(-1001, "timezone", "Europe/Warsaw")
    await repository.record_message(
        chat_id=-1001,
        user=UserData(101, None, "Dmytro", None, "uk"),
        activity=MessageActivity(False, False),
        occurred_at=datetime.now(UTC),
        message_id=1,
    )
    await repository.reset_group_stats(-1001)
    assert (await repository.get_group_summary(-1001))["messages_count"] == 0
    settings = await repository.get_group_settings(-1001)
    assert settings is not None
    assert settings["timezone"] == "Europe/Warsaw"
