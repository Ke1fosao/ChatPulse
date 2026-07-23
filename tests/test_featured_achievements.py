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
        codes = ["messages_10", "messages_100", "messages_500", "replies_10", "replies_50"]
        session.add_all(
            [
                AchievementUnlockRecord(
                    telegram_user_id=202,
                    telegram_chat_id=-1001,
                    scope="group",
                    scope_key="group:-1001",
                    achievement_code=code,
                    rarity="common",
                    final_progress=(index + 1) * 10,
                    definition_version=2,
                    earned_at=datetime(2026, 7, 23, 10 + index, 0, tzinfo=UTC),
                )
                for index, code in enumerate(codes)
            ]
        )
    yield FeaturedAchievementRepository(database.session_factory)
    await database.dispose()


@pytest.mark.asyncio
async def test_user_can_pin_and_reorder_five_earned_achievements(featured_repository) -> None:
    codes = ["messages_10", "messages_100", "messages_500", "replies_10", "replies_50"]

    first = await featured_repository.set_featured_codes(202, codes)
    reordered = await featured_repository.set_featured_codes(202, list(reversed(codes)))

    assert [item["code"] for item in first] == codes
    assert [item["slot"] for item in reordered] == [1, 2, 3, 4, 5]
    assert [item["code"] for item in reordered] == list(reversed(codes))


@pytest.mark.asyncio
async def test_user_cannot_pin_unearned_or_more_than_five_achievements(
    featured_repository,
) -> None:
    with pytest.raises(ValueError, match="отримані"):
        await featured_repository.set_featured_codes(202, ["messages_1000"])

    with pytest.raises(ValueError, match="не більше пʼяти"):
        await featured_repository.set_featured_codes(
            202,
            [
                "messages_10",
                "messages_100",
                "messages_500",
                "replies_10",
                "replies_50",
                "messages_1000",
            ],
        )


@pytest.mark.asyncio
async def test_user_can_clear_featured_achievements(featured_repository) -> None:
    await featured_repository.set_featured_codes(202, ["messages_10"])

    assert await featured_repository.set_featured_codes(202, []) == []
    assert await featured_repository.list_featured(202) == []
