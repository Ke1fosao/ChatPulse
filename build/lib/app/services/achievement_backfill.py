from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.achievement_models import AchievementEventRecord, AchievementUnlockRecord
from app.achievements.catalog import ACHIEVEMENT_BY_CODE, AchievementRarity
from app.achievements.engine import AchievementEvent, AchievementSnapshot
from app.models import ChatGroup, DailyActivity, GroupMember, MemberAchievement, User, utc_now
from app.repositories.achievements import AchievementRepository, achievement_scope_key
from app.repositories.gamification_v2 import AchievementGamificationRepository

RARITY_WEIGHT = {
    AchievementRarity.COMMON: 1,
    AchievementRarity.UNCOMMON: 2,
    AchievementRarity.RARE: 3,
    AchievementRarity.EPIC: 4,
    AchievementRarity.LEGENDARY: 5,
    AchievementRarity.SECRET: 6,
}


class AchievementBackfillService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._achievement_repository = AchievementRepository(session_factory)

    async def run(self, *, now: datetime | None = None) -> dict[str, int]:
        timestamp = (now or utc_now()).astimezone(UTC)
        added_by_user: defaultdict[int, list[str]] = defaultdict(list)

        async with self._session_factory() as session, session.begin():
            imported_legacy = await self._import_legacy_unlocks(
                session,
                added_by_user,
            )
            recalculated = await self._recalculate_members(
                session,
                timestamp=timestamp,
                added_by_user=added_by_user,
            )
            summary_events = await self._create_summary_events(
                session,
                timestamp=timestamp,
                added_by_user=added_by_user,
            )

        return {
            "users_updated": len(added_by_user),
            "legacy_imported": imported_legacy,
            "recalculated_unlocks": recalculated,
            "summary_events": summary_events,
        }

    async def _import_legacy_unlocks(
        self,
        session: AsyncSession,
        added_by_user: defaultdict[int, list[str]],
    ) -> int:
        existing_rows = (
            await session.execute(
                select(
                    AchievementUnlockRecord.telegram_user_id,
                    AchievementUnlockRecord.scope_key,
                    AchievementUnlockRecord.achievement_code,
                )
            )
        ).all()
        existing = {(int(row[0]), str(row[1]), str(row[2])) for row in existing_rows}
        rows = (
            await session.scalars(
                select(MemberAchievement).order_by(
                    MemberAchievement.telegram_user_id.asc(),
                    MemberAchievement.earned_at.asc(),
                )
            )
        ).all()
        imported = 0
        for legacy in rows:
            definition = ACHIEVEMENT_BY_CODE.get(legacy.achievement_code)
            if definition is None:
                continue
            scope_key = achievement_scope_key("group", legacy.telegram_chat_id)
            identity = (
                int(legacy.telegram_user_id),
                scope_key,
                str(legacy.achievement_code),
            )
            if identity in existing:
                continue
            session.add(
                AchievementUnlockRecord(
                    telegram_user_id=legacy.telegram_user_id,
                    telegram_chat_id=legacy.telegram_chat_id,
                    scope="group",
                    scope_key=scope_key,
                    achievement_code=legacy.achievement_code,
                    rarity=definition.rarity.value,
                    final_progress=definition.threshold,
                    definition_version=definition.version,
                    earned_at=legacy.earned_at,
                )
            )
            existing.add(identity)
            added_by_user[legacy.telegram_user_id].append(legacy.achievement_code)
            imported += 1
        await session.flush()
        return imported

    async def _recalculate_members(
        self,
        session: AsyncSession,
        *,
        timestamp: datetime,
        added_by_user: defaultdict[int, list[str]],
    ) -> int:
        start_date = timestamp.date() - timedelta(days=6)
        rows = (
            await session.execute(
                select(GroupMember, User)
                .join(User, User.telegram_id == GroupMember.telegram_user_id)
                .order_by(
                    GroupMember.telegram_user_id.asc(),
                    GroupMember.telegram_chat_id.asc(),
                )
            )
        ).all()
        recalculated = 0
        for member, user in rows:
            values = dict(AchievementGamificationRepository._live_snapshot(member, user).values)
            values.update(
                await self._extended_metrics(
                    session,
                    member=member,
                    start_date=start_date,
                )
            )
            events = tuple(
                AchievementEvent(
                    trigger=trigger,
                    telegram_user_id=member.telegram_user_id,
                    telegram_chat_id=member.telegram_chat_id,
                    occurred_at=timestamp,
                )
                for trigger in (
                    "message_created",
                    "reply_created",
                    "media_created",
                    "reaction_received",
                    "streak_updated",
                    "level_changed",
                    "ranking_calculated",
                    "weekly_report_created",
                )
            )
            earned = await self._achievement_repository.record_events(
                session,
                events=events,
                snapshot=AchievementSnapshot(values=values),
                create_events=False,
            )
            if not earned:
                continue
            codes = [item.code for item in earned]
            added_by_user[member.telegram_user_id].extend(codes)
            recalculated += len(codes)
        return recalculated

    async def _extended_metrics(
        self,
        session: AsyncSession,
        *,
        member: GroupMember,
        start_date: date,
    ) -> dict[str, int]:
        rank = (
            int(
                await session.scalar(
                    select(func.count())
                    .select_from(GroupMember)
                    .where(
                        GroupMember.telegram_chat_id == member.telegram_chat_id,
                        GroupMember.xp_total > member.xp_total,
                    )
                )
                or 0
            )
            + 1
        )
        groups_count = int(
            await session.scalar(
                select(func.count())
                .select_from(GroupMember)
                .join(
                    ChatGroup,
                    ChatGroup.telegram_chat_id == GroupMember.telegram_chat_id,
                )
                .where(
                    GroupMember.telegram_user_id == member.telegram_user_id,
                    ChatGroup.is_active.is_(True),
                )
            )
            or 0
        )
        active_days_total = int(
            await session.scalar(
                select(func.count(func.distinct(DailyActivity.activity_date))).where(
                    DailyActivity.telegram_user_id == member.telegram_user_id,
                    DailyActivity.xp_earned > 0,
                )
            )
            or 0
        )
        xp_7d = int(
            await session.scalar(
                select(func.coalesce(func.sum(DailyActivity.xp_earned), 0)).where(
                    DailyActivity.telegram_chat_id == member.telegram_chat_id,
                    DailyActivity.telegram_user_id == member.telegram_user_id,
                    DailyActivity.activity_date >= start_date,
                )
            )
            or 0
        )
        return {
            "rank": rank,
            "groups_count": groups_count,
            "active_days_total": active_days_total,
            "xp_7d": xp_7d,
        }

    async def _create_summary_events(
        self,
        session: AsyncSession,
        *,
        timestamp: datetime,
        added_by_user: defaultdict[int, list[str]],
    ) -> int:
        created = 0
        for user_id, codes in added_by_user.items():
            unique_codes = list(dict.fromkeys(codes))
            if not unique_codes:
                continue
            existing = await session.scalar(
                select(AchievementEventRecord.id).where(
                    AchievementEventRecord.telegram_user_id == user_id,
                    AchievementEventRecord.event_type == "collection_update",
                    AchievementEventRecord.seen_at.is_(None),
                )
            )
            if existing is not None:
                continue
            rarest_codes = sorted(
                unique_codes,
                key=lambda code: RARITY_WEIGHT[ACHIEVEMENT_BY_CODE[code].rarity],
                reverse=True,
            )[:3]
            self._achievement_repository.add_collection_update_event(
                session,
                user_id=user_id,
                count=len(unique_codes),
                rarest_codes=rarest_codes,
                created_at=timestamp,
            )
            created += 1
        return created
