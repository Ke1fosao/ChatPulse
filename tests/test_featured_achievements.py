from datetime import UTC, datetime

import pytest

from app.achievement_models import AchievementUnlockRecord
from app.database import Database
from app.models import ChatGroup, User
from app.repositories.featured_achievements import FeaturedAchievementRepository


@pytest.fixture
async def featured_repository(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'featured.db'}")
    await database.create_schema()
    async with database.session_factory() as session, session.begin():
        session.add(User(telegram_id=202, username="client", first_name="Client"))
        session.add(
            ChatGroup(
                telegram_chat_id=-1001,
                title="Test group",
                is_active=True,
                bot_status="administrator",
            )
        )
        session.add_all(
            [
                AchievementUnlockRecord(
                    telegram_user_id=202,
                    telegram_chat_id=-1001,
                    scope="group",
                    scope_key="group:-1001",
                    achievement_code="first_steps",
                    rarity="common",
                    final_progress=10,
                    definition_version=2,
                    earned_at=datetime(2026, 7, 23, 10, 0, tzinfo=UTC),
                ),
                AchievementUnlockRecord(
                    telegram_user_id=202,
                    telegram_chat_id=-1001,
                    scope="group",
                    scope_key="group:-1001",
                    achievement_code="xp_100",
                    rarity="uncommon",
                    final_progress=100,
                    definition_version=2,
                    earned_at=datetime(2026, 7, 23, 11, 0, tzinfo=UTC),
                ),
            ]
        )
    yield FeaturedAchievementRepository(database.session_factory)
    await database.dispose()


@pytest.mark.asyncio
async def test_user_can_pin_and_reorder_earned_achievements(featured_repository) -> None:
    first = await featured_repository.set_featured_codes(
        202,
        ["first_steps", "xp_100"],
    )
    reordered = await featured_repository.set_featured_codes(
        202,
        ["xp_100", "first_steps"],
    )

    assert [item["code"] for item in first] == ["first_steps", "xp_100"]
    assert [item["slot"] for item in reordered] == [1, 2]
    assert [item["code"] for item in reordered] == ["xp_100", "first_steps"]


@pytest.mark.asyncio
async def test_user_cannot_pin_unearned_or_more_than_three_achievements(
    featured_repository,
) -> None:
    with pytest.raises(ValueError, match="отримані"):
        await featured_repository.set_featured_codes(202, ["xp_500"])

    with pytest.raises(ValueError, match="не більше трьох"):
        await featured_repository.set_featured_codes(
            202,
            ["first_steps", "xp_100", "xp_500", "xp_1000"],
        )


@pytest.mark.asyncio
async def test_user_can_clear_featured_achievements(featured_repository) -> None:
    await featured_repository.set_featured_codes(202, ["first_steps"])

    assert await featured_repository.set_featured_codes(202, []) == []
    assert await featured_repository.list_featured(202) == []
