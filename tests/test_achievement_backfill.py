from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.achievement_models import AchievementEventRecord, AchievementUnlockRecord
from app.database import Database
from app.models import ChatGroup, GroupMember, MemberAchievement, User
from app.services.achievement_backfill import AchievementBackfillService


@pytest.mark.asyncio
async def test_backfill_is_idempotent_and_creates_one_summary_event(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'achievement-backfill.db'}")
    await database.create_schema()
    earned_at = datetime(2026, 7, 1, 10, tzinfo=UTC)

    async with database.session_factory() as session, session.begin():
        session.add(
            User(
                telegram_id=101,
                username="dmytro",
                first_name="Dmytro",
                last_name=None,
                language_code="uk",
                global_xp_total=5_000,
                global_level=10,
                created_at=earned_at,
                updated_at=earned_at,
                last_activity_at=earned_at,
            )
        )
        session.add(
            ChatGroup(
                telegram_chat_id=-1001,
                title="ChatPulse Team",
                username=None,
                bot_status="administrator",
                is_active=True,
                timezone="Europe/Kyiv",
            )
        )
        session.add(
            GroupMember(
                telegram_chat_id=-1001,
                telegram_user_id=101,
                display_name="Dmytro",
                username="dmytro",
                messages_count=1_000,
                media_count=120,
                replies_count=100,
                reactions_received=250,
                photo_count=80,
                voice_count=40,
                night_messages_count=20,
                morning_messages_count=20,
                xp_total=1_000,
                level=5,
                current_streak=7,
                longest_streak=7,
                first_seen_at=earned_at,
                last_seen_at=earned_at,
            )
        )
        session.add(
            MemberAchievement(
                telegram_chat_id=-1001,
                telegram_user_id=101,
                achievement_code="first_steps",
                earned_at=earned_at,
            )
        )

    service = AchievementBackfillService(database.session_factory)
    first = await service.run(now=datetime(2026, 7, 22, 12, tzinfo=UTC))
    second = await service.run(now=datetime(2026, 7, 22, 13, tzinfo=UTC))

    assert first["legacy_imported"] == 1
    assert first["recalculated_unlocks"] > 1
    assert first["summary_events"] == 1
    assert second == {
        "users_updated": 0,
        "legacy_imported": 0,
        "recalculated_unlocks": 0,
        "summary_events": 0,
    }

    async with database.session_factory() as session:
        codes = set(
            (
                await session.scalars(
                    select(AchievementUnlockRecord.achievement_code).where(
                        AchievementUnlockRecord.telegram_user_id == 101
                    )
                )
            ).all()
        )
        event_count = int(
            await session.scalar(select(func.count()).select_from(AchievementEventRecord)) or 0
        )
        event_types = set((await session.scalars(select(AchievementEventRecord.event_type))).all())

    assert "first_steps" in codes
    assert "messages_100" in codes
    assert "messages_1000" in codes
    assert "global_xp_1000" in codes
    assert event_count == 1
    assert event_types == {"collection_update"}

    await database.dispose()
