from datetime import UTC, datetime

import pytest

from app.achievement_models import AchievementUnlockRecord
from app.database import Database
from app.models import User
from app.repositories.featured_achievements import FeaturedAchievementRepository


@pytest.fixture
async def featured_repository(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'featured.db'}")
    await database.create_schema()
    async with database.session_factory() as session, session.begin():
        session.add(User(telegram_id=202, username="client", first_name="Client"))
        session.add_all(
            [
                AchievementUnlockRecord(
                    telegram_user_id=202,
                    telegram_chat_id=None,
                    scope="global",
                    scope_key="global",
                    achievement_code="global_xp_100",
                    rarity="common",
                    final_progress=100,
                    definition_version=2,
                    earned_at=datetime(2026, 7, 23, 10, 0, tzinfo=UTC),
                ),
                AchievementUnlockRecord(
                    telegram_user_id=202,
                    telegram_chat_id=None,
                    scope="global",
                    scope_key="global",
                    achievement_code="global_xp_500",
                    rarity="uncommon",
                    final_progress=500,
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
        ["global_xp_100", "global_xp_500"],
    )
    reordered = await featured_repository.set_featured_codes(
        202,
        ["global_xp_500", "global_xp_100"],
    )

    assert [item["code"] for item in first] == ["global_xp_100", "global_xp_500"]
    assert [item["slot"] for item in reordered] == [1, 2]
    assert [item["code"] for item in reordered] == ["global_xp_500", "global_xp_100"]


@pytest.mark.asyncio
async def test_user_cannot_pin_unearned_or_more_than_three_achievements(
    featured_repository,
) -> None:
    with pytest.raises(ValueError, match="отримані"):
        await featured_repository.set_featured_codes(202, ["global_xp_1000"])

    with pytest.raises(ValueError, match="не більше трьох"):
        await featured_repository.set_featured_codes(
            202,
            ["global_xp_100", "global_xp_500", "global_xp_1000", "global_xp_5000"],
        )


@pytest.mark.asyncio
async def test_user_can_clear_featured_achievements(featured_repository) -> None:
    await featured_repository.set_featured_codes(202, ["global_xp_100"])

    assert await featured_repository.set_featured_codes(202, []) == []
    assert await featured_repository.list_featured(202) == []
