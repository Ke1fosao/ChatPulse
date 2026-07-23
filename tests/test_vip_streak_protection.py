from datetime import UTC, date, datetime, timedelta

import pytest

from app.database import Database
from app.models import ChatGroup, User, VipGrant
from app.repositories.gamification_v2 import AchievementGamificationRepository


@pytest.mark.asyncio
async def test_vip_can_consume_five_monthly_streak_protections(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'vip-streak.db'}")
    await database.create_schema()
    now = datetime.now(UTC)
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(telegram_id=505, first_name="VIP"),
                ChatGroup(telegram_chat_id=-505, title="VIP group", is_active=True),
                VipGrant(
                    telegram_user_id=505,
                    is_active=True,
                    starts_at=now,
                    expires_at=now + timedelta(days=30),
                    granted_by_owner_id=1,
                    grant_reason="paid VIP",
                ),
            ]
        )

    repository = AchievementGamificationRepository(database.session_factory)
    missing = [date(2026, 7, day) for day in range(1, 6)]
    async with database.session_factory() as session, session.begin():
        assert await repository._consume_protections(session, -505, 505, missing) is True

    await database.dispose()


@pytest.mark.asyncio
async def test_free_user_remains_limited_to_three_protections(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'free-streak.db'}")
    await database.create_schema()
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(telegram_id=303, first_name="Free"),
                ChatGroup(telegram_chat_id=-303, title="Free group", is_active=True),
            ]
        )

    repository = AchievementGamificationRepository(database.session_factory)
    missing = [date(2026, 7, day) for day in range(1, 5)]
    async with database.session_factory() as session, session.begin():
        assert await repository._consume_protections(session, -303, 303, missing) is False

    await database.dispose()
