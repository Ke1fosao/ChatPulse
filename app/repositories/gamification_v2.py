from collections import Counter
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.achievements.engine import AchievementEvent, AchievementSnapshot
from app.domain import AchievementEarned
from app.models import (
    BotOwner,
    ChatGroup,
    DailyActivity,
    GroupMember,
    StreakProtectionUsage,
    User,
    VipGrant,
    utc_now,
)
from app.repositories.achievements import AchievementRepository
from app.repositories.gamification import GamificationRepository
from app.services.gamification import MONTHLY_PROTECTION_DAYS, level_for_xp

VIP_MONTHLY_PROTECTION_DAYS = 5


class AchievementGamificationRepository(GamificationRepository):
    """Adds Achievement System 2.0 and premium streak protection to the XP pipeline."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory)
        self._achievement_v2 = AchievementRepository(session_factory)

    async def _consume_protections(
        self,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        missing_dates: list[date],
    ) -> bool:
        if not missing_dates:
            return True

        now = utc_now()
        owner = await session.get(BotOwner, "primary")
        grant = await session.get(VipGrant, user_id)
        is_owner = bool(owner and int(owner.telegram_user_id) == user_id)
        is_vip = bool(
            grant
            and grant.is_active
            and (grant.expires_at is None or self._aware(grant.expires_at) > now)
        )
        limit = VIP_MONTHLY_PROTECTION_DAYS if is_owner or is_vip else MONTHLY_PROTECTION_DAYS

        required = Counter(item.replace(day=1) for item in missing_dates)
        usages: dict[date, StreakProtectionUsage] = {}
        for month_start, needed in required.items():
            usage = await session.get(
                StreakProtectionUsage,
                (chat_id, user_id, month_start),
            )
            if usage is None:
                usage = StreakProtectionUsage(
                    telegram_chat_id=chat_id,
                    telegram_user_id=user_id,
                    month_start=month_start,
                    used_days=0,
                )
                session.add(usage)
                await session.flush()
            if usage.used_days + needed > limit:
                return False
            usages[month_start] = usage
        for month_start, needed in required.items():
            usages[month_start].used_days += needed
        return True

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _apply_achievement_rewards(
        member: GroupMember,
        user: User,
        earned: list[AchievementEarned],
    ) -> None:
        group_reward = sum(
            max(0, int(item.reward_xp)) for item in earned if item.scope == "group"
        )
        global_reward = sum(max(0, int(item.reward_xp)) for item in earned)
        if group_reward:
            member.xp_total += group_reward
            member.level = level_for_xp(member.xp_total)
        if global_reward:
            user.global_xp_total += global_reward
            user.global_level = level_for_xp(user.global_xp_total)

    async def _award_new_achievements(
        self,
        session: AsyncSession,
        member: GroupMember,
        timestamp: datetime,
    ) -> list[AchievementEarned]:
        user = await session.get(User, member.telegram_user_id)
        if user is None:
            return []

        snapshot = self._live_snapshot(member, user)
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
            )
        )
        earned = await self._achievement_v2.record_events(
            session,
            events=events,
            snapshot=snapshot,
        )
        self._apply_achievement_rewards(member, user, earned)
        return earned

    async def evaluate_weekly_achievements(
        self,
        chat_id: int,
        *,
        now: datetime | None = None,
    ) -> int:
        timestamp = (now or utc_now()).astimezone(UTC)
        start_date = timestamp.date() - timedelta(days=6)
        unlocked = 0

        async with self._session_factory() as session, session.begin():
            rows = (
                await session.execute(
                    select(GroupMember, User)
                    .join(User, User.telegram_id == GroupMember.telegram_user_id)
                    .where(GroupMember.telegram_chat_id == chat_id)
                    .order_by(GroupMember.telegram_user_id.asc())
                )
            ).all()
            for row in rows:
                member = row.GroupMember
                user = row.User
                rank = (
                    int(
                        await session.scalar(
                            select(func.count())
                            .select_from(GroupMember)
                            .where(
                                GroupMember.telegram_chat_id == chat_id,
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
                            DailyActivity.telegram_chat_id == chat_id,
                            DailyActivity.telegram_user_id == member.telegram_user_id,
                            DailyActivity.activity_date >= start_date,
                        )
                    )
                    or 0
                )
                values = dict(self._live_snapshot(member, user).values)
                values.update(
                    {
                        "rank": rank,
                        "groups_count": groups_count,
                        "active_days_total": active_days_total,
                        "xp_7d": xp_7d,
                    }
                )
                events = (
                    AchievementEvent(
                        trigger="weekly_report_created",
                        telegram_user_id=member.telegram_user_id,
                        telegram_chat_id=chat_id,
                        occurred_at=timestamp,
                    ),
                    AchievementEvent(
                        trigger="ranking_calculated",
                        telegram_user_id=member.telegram_user_id,
                        telegram_chat_id=chat_id,
                        occurred_at=timestamp,
                    ),
                )
                earned = await self._achievement_v2.record_events(
                    session,
                    events=events,
                    snapshot=AchievementSnapshot(values=values),
                )
                self._apply_achievement_rewards(member, user, earned)
                unlocked += len(earned)
        return unlocked

    @staticmethod
    def _live_snapshot(member: GroupMember, user: User) -> AchievementSnapshot:
        return AchievementSnapshot(
            values={
                "messages_count": int(member.messages_count),
                "media_count": int(member.media_count),
                "replies_count": int(member.replies_count),
                "reactions_received": int(member.reactions_received),
                "photo_count": int(member.photo_count),
                "voice_count": int(member.voice_count),
                "night_messages_count": int(member.night_messages_count),
                "morning_messages_count": int(member.morning_messages_count),
                "xp_total": int(member.xp_total),
                "level": int(member.level),
                "current_streak": int(member.current_streak),
                "global_xp_total": int(user.global_xp_total),
                "global_level": int(user.global_level),
            }
        )
