from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.database import Database
from app.domain import GroupData
from app.models import ChatGroup
from app.repositories.activity import ActivityRepository
from app.services.group_status_sync import (
    reconcile_group_bot_status,
    upsert_group_from_message,
)
from app.services.telegram_access import TelegramAccessService


@pytest.mark.asyncio
async def test_message_refresh_keeps_known_administrator_status(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'status.db'}")
    await database.create_schema()
    repository = ActivityRepository(database.session_factory)

    await repository.upsert_group(
        GroupData(-1001, "Old title", None, "Europe/Kyiv"),
        bot_status="administrator",
        is_active=True,
    )
    await upsert_group_from_message(
        repository,
        GroupData(-1001, "Updated title", "updated_group", "Europe/Kyiv"),
    )

    async with database.session_factory() as session:
        group = await session.get(ChatGroup, -1001)
        assert group is not None
        assert group.bot_status == "administrator"
        assert group.title == "Updated title"
        assert group.username == "updated_group"

    await database.dispose()


@pytest.mark.asyncio
async def test_authoritative_telegram_status_repairs_stale_database_value(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'reconcile.db'}")
    await database.create_schema()
    repository = ActivityRepository(database.session_factory)

    await repository.upsert_group(
        GroupData(-1001, "Group", None, "Europe/Kyiv"),
        bot_status="member",
        is_active=True,
    )

    assert await reconcile_group_bot_status(
        database.session_factory,
        -1001,
        "administrator",
    )

    async with database.session_factory() as session:
        group = await session.get(ChatGroup, -1001)
        assert group is not None
        assert group.bot_status == "administrator"
        assert group.is_active is True

    await database.dispose()


@pytest.mark.asyncio
async def test_bot_identity_is_resolved_once_for_status_checks() -> None:
    bot = SimpleNamespace(
        get_me=AsyncMock(return_value=SimpleNamespace(id=777)),
        get_chat_member=AsyncMock(
            return_value=SimpleNamespace(status=SimpleNamespace(value="administrator"))
        ),
    )
    service = TelegramAccessService(bot)

    assert await service.get_bot_status(-1001) == "administrator"
    assert await service.get_bot_status(-1002) == "administrator"
    bot.get_me.assert_awaited_once()
    assert bot.get_chat_member.await_count == 2
