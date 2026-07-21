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


@pytest.mark.asyncio
async def test_user_and_group_upserts_are_idempotent(repository: ActivityRepository) -> None:
    user = UserData(
        telegram_id=101,
        username="dmytro",
        first_name="Dmytro",
        last_name=None,
        language_code="uk",
    )
    group = GroupData(
        telegram_chat_id=-1001,
        title="Test group",
        username=None,
        timezone="Europe/Kyiv",
    )

    await repository.upsert_user(user)
    await repository.upsert_user(
        UserData(
            telegram_id=101,
            username="dmytro_new",
            first_name="Dmytro",
            last_name="K",
            language_code="uk",
        )
    )
    await repository.upsert_group(group, bot_status="member", is_active=False)
    await repository.upsert_group(group, bot_status="administrator", is_active=True)

    member = await repository.get_member_stats(-1001, 101)
    summary = await repository.get_group_summary(-1001)

    assert member is None
    assert summary == {
        "messages_count": 0,
        "media_count": 0,
        "replies_count": 0,
        "active_members": 0,
    }


@pytest.mark.asyncio
async def test_record_message_updates_member_and_daily_counters(
    repository: ActivityRepository,
) -> None:
    user = UserData(101, "dmytro", "Dmytro", None, "uk")
    group = GroupData(-1001, "Test group", None, "Europe/Kyiv")
    await repository.upsert_user(user)
    await repository.upsert_group(group, bot_status="administrator", is_active=True)

    recorded = await repository.record_message(
        chat_id=-1001,
        user=user,
        activity=MessageActivity(is_media=True, is_reply=True),
        occurred_at=datetime(2026, 7, 21, 17, 30, tzinfo=UTC),
    )
    await repository.record_message(
        chat_id=-1001,
        user=user,
        activity=MessageActivity(is_media=False, is_reply=False),
        occurred_at=datetime(2026, 7, 21, 17, 31, tzinfo=UTC),
    )

    member = await repository.get_member_stats(-1001, 101)
    summary = await repository.get_group_summary(-1001)
    top = await repository.get_top_members(-1001, limit=5)

    assert recorded is True
    assert member == {
        "telegram_user_id": 101,
        "display_name": "Dmytro",
        "username": "dmytro",
        "messages_count": 2,
        "media_count": 1,
        "replies_count": 1,
    }
    assert summary == {
        "messages_count": 2,
        "media_count": 1,
        "replies_count": 1,
        "active_members": 1,
    }
    assert top == [member]


@pytest.mark.asyncio
async def test_inactive_group_does_not_record_activity(repository: ActivityRepository) -> None:
    user = UserData(101, "dmytro", "Dmytro", None, "uk")
    group = GroupData(-1001, "Test group", None, "Europe/Kyiv")
    await repository.upsert_user(user)
    await repository.upsert_group(group, bot_status="member", is_active=False)

    recorded = await repository.record_message(
        chat_id=-1001,
        user=user,
        activity=MessageActivity(is_media=False, is_reply=False),
        occurred_at=datetime.now(UTC),
    )

    assert recorded is False
    assert await repository.get_member_stats(-1001, 101) is None
