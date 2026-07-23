from datetime import UTC, datetime

import pytest

from app.achievement_models import AchievementUnlockRecord
from app.database import Database
from app.models import ChatGroup, GroupMember, User
from app.repositories.miniapp_v2 import AchievementMiniAppRepository


@pytest.mark.asyncio
async def test_group_achievement_exposes_each_earned_instance(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'instances.db'}")
    await database.create_schema()
    async with database.session_factory() as session, session.begin():
        session.add(User(telegram_id=501, username="collector", first_name="Collector"))
        session.add_all(
            [
                ChatGroup(
                    telegram_chat_id=-1001,
                    title="Design Team",
                    is_active=True,
                    bot_status="administrator",
                ),
                ChatGroup(
                    telegram_chat_id=-1002,
                    title="Dev Team",
                    is_active=True,
                    bot_status="administrator",
                ),
            ]
        )
        session.add_all(
            [
                GroupMember(
                    telegram_chat_id=-1001,
                    telegram_user_id=501,
                    display_name="Collector",
                    messages_count=120,
                ),
                GroupMember(
                    telegram_chat_id=-1002,
                    telegram_user_id=501,
                    display_name="Collector",
                    messages_count=240,
                ),
            ]
        )
        session.add_all(
            [
                AchievementUnlockRecord(
                    telegram_user_id=501,
                    telegram_chat_id=-1001,
                    scope="group",
                    scope_key="group:-1001",
                    achievement_code="messages_100",
                    rarity="uncommon",
                    final_progress=120,
                    definition_version=2,
                    earned_at=datetime(2026, 7, 20, 10, 0, tzinfo=UTC),
                ),
                AchievementUnlockRecord(
                    telegram_user_id=501,
                    telegram_chat_id=-1002,
                    scope="group",
                    scope_key="group:-1002",
                    achievement_code="messages_100",
                    rarity="uncommon",
                    final_progress=240,
                    definition_version=2,
                    earned_at=datetime(2026, 7, 21, 10, 0, tzinfo=UTC),
                ),
            ]
        )

    repository = AchievementMiniAppRepository(database.session_factory)
    achievements = await repository.get_achievements(501)
    assert achievements is not None
    item = next(value for value in achievements if value["code"] == "messages_100")

    assert item["primary_scope_key"] == "group:-1002"
    assert item["group_title"] == "Dev Team"
    assert item["earned_instances"] == [
        {
            "scope_key": "group:-1002",
            "telegram_chat_id": -1002,
            "group_title": "Dev Team",
            "earned_at": "2026-07-21T10:00:00",
            "progress": 240,
        },
        {
            "scope_key": "group:-1001",
            "telegram_chat_id": -1001,
            "group_title": "Design Team",
            "earned_at": "2026-07-20T10:00:00",
            "progress": 120,
        },
    ]

    await database.dispose()
