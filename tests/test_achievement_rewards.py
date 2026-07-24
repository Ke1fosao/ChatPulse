from datetime import UTC, datetime

import pytest

from app.database import Database
from app.models import ChatGroup, GroupMember, User
from app.repositories.gamification_v2 import AchievementGamificationRepository


async def _seed(database: Database, *, global_xp: int = 0, messages: int = 0) -> None:
    async with database.session_factory() as session, session.begin():
        session.add(
            User(
                telegram_id=701,
                username="rewarded",
                first_name="Rewarded",
                global_xp_total=global_xp,
            )
        )
        session.add(
            ChatGroup(
                telegram_chat_id=-7001,
                title="Rewards",
                is_active=True,
                bot_status="administrator",
            )
        )
        session.add(
            GroupMember(
                telegram_chat_id=-7001,
                telegram_user_id=701,
                display_name="Rewarded",
                messages_count=messages,
            )
        )


@pytest.mark.asyncio
async def test_group_unlock_awards_group_and_global_xp_once(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'group-reward.db'}")
    await database.create_schema()
    await _seed(database, messages=10)
    repository = AchievementGamificationRepository(database.session_factory)

    async with database.session_factory() as session, session.begin():
        member = await session.get(GroupMember, (-7001, 701))
        assert member is not None
        first = await repository._award_new_achievements(
            session,
            member,
            datetime(2026, 7, 24, 10, 0, tzinfo=UTC),
        )
        second = await repository._award_new_achievements(
            session,
            member,
            datetime(2026, 7, 24, 10, 1, tzinfo=UTC),
        )
        user = await session.get(User, 701)
        assert user is not None

        assert [(item.code, item.reward_xp, item.scope) for item in first] == [
            ("messages_10", 5, "group")
        ]
        assert second == []
        assert member.xp_total == 5
        assert user.global_xp_total == 5

    await database.dispose()


@pytest.mark.asyncio
async def test_global_unlock_awards_only_global_xp(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'global-reward.db'}")
    await database.create_schema()
    await _seed(database, global_xp=1000)
    repository = AchievementGamificationRepository(database.session_factory)

    async with database.session_factory() as session, session.begin():
        member = await session.get(GroupMember, (-7001, 701))
        assert member is not None
        earned = await repository._award_new_achievements(
            session,
            member,
            datetime(2026, 7, 24, 11, 0, tzinfo=UTC),
        )
        user = await session.get(User, 701)
        assert user is not None

        global_reward = next(item for item in earned if item.code == "global_xp_1000")
        assert global_reward.reward_xp == 5
        assert global_reward.scope == "global"
        assert member.xp_total == 0
        assert user.global_xp_total == 1005

    await database.dispose()
