from collections import Counter
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain import AchievementEarned, GamificationUpdate, MessageActivity
from app.models import (
    ChatGroup,
    DailyActivity,
    GlobalDailyXP,
    GroupMember,
    MemberAchievement,
    MessageAuthor,
    StreakProtectionUsage,
    User,
    utc_now,
)
from app.services.gamification import (
    ACHIEVEMENT_BY_CODE,
    BURST_WINDOW_MINUTES,
    GLOBAL_DAILY_XP_CAP,
    GROUP_DAILY_XP_CAP,
    MONTHLY_PROTECTION_DAYS,
    STREAK_XP_THRESHOLD,
    XP_COOLDOWN_SECONDS,
    adjusted_message_xp,
    evaluate_achievements,
    hamming_distance,
    level_for_xp,
    message_base_xp,
)

SUMMARY_FIELDS = (
    "messages_count",
    "media_count",
    "replies_count",
    "reactions_received",
    "photo_count",
    "voice_count",
    "night_messages_count",
    "morning_messages_count",
    "xp_earned",
)


class GamificationRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_group_extras(self, chat_id: int) -> dict[str, Any]:
        async with self._session_factory() as session:
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                return {"report_card_theme": "dark_pulse", "report_minute": 0}
            return {
                "report_card_theme": group.report_card_theme,
                "report_minute": group.report_minute,
            }

    async def update_report_time(self, chat_id: int, *, hour: int, minute: int) -> None:
        async with self._session_factory() as session, session.begin():
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                raise LookupError("Group is not registered")
            group.report_hour = hour
            group.report_minute = minute
            group.updated_at = utc_now()

    async def cycle_report_theme(self, chat_id: int) -> str:
        themes = ("dark_pulse", "telegram_wave", "clean_light")
        async with self._session_factory() as session, session.begin():
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                raise LookupError("Group is not registered")
            current = group.report_card_theme if group.report_card_theme in themes else themes[0]
            group.report_card_theme = themes[(themes.index(current) + 1) % len(themes)]
            group.updated_at = utc_now()
            return group.report_card_theme

    async def reset_group_gamification(self, chat_id: int) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                delete(MemberAchievement).where(MemberAchievement.telegram_chat_id == chat_id)
            )
            await session.execute(
                delete(StreakProtectionUsage).where(
                    StreakProtectionUsage.telegram_chat_id == chat_id
                )
            )

    async def update_message_reaction_total(
        self,
        chat_id: int,
        message_id: int,
        *,
        delta: int | None = None,
        total: int | None = None,
    ) -> tuple[int, int]:
        async with self._session_factory() as session, session.begin():
            author = await session.get(MessageAuthor, (chat_id, message_id))
            if author is None:
                return 0, 0
            previous = int(author.reactions_count)
            new_total = int(total) if total is not None else previous + int(delta or 0)
            author.reactions_count = max(0, new_total)
            return previous, int(author.reactions_count)

    async def award_message_xp(
        self,
        *,
        chat_id: int,
        user_id: int,
        message_id: int,
        activity: MessageActivity,
        occurred_at: datetime,
    ) -> GamificationUpdate:
        timestamp = occurred_at.astimezone(UTC)
        async with self._session_factory() as session, session.begin():
            group = await session.get(ChatGroup, chat_id)
            member = await session.get(GroupMember, (chat_id, user_id))
            user = await session.get(User, user_id)
            author = await session.get(MessageAuthor, (chat_id, message_id))
            if group is None or member is None or user is None or author is None:
                return GamificationUpdate()

            author.content_fingerprint = activity.content_fingerprint
            author.content_simhash = (
                f"{activity.content_simhash:016x}" if activity.content_simhash is not None else None
            )
            author.content_length = activity.content_length

            window_start = timestamp - timedelta(minutes=BURST_WINDOW_MINUTES)
            result = await session.scalars(
                select(MessageAuthor)
                .where(
                    MessageAuthor.telegram_chat_id == chat_id,
                    MessageAuthor.telegram_user_id == user_id,
                    MessageAuthor.message_id != message_id,
                    MessageAuthor.created_at >= window_start,
                    MessageAuthor.created_at <= timestamp,
                )
                .order_by(MessageAuthor.created_at.desc())
            )
            recent = list(result.all())
            latest_awarded = next((item for item in recent if item.xp_awarded > 0), None)
            latest_created_at = latest_awarded.created_at if latest_awarded else None
            if latest_created_at is not None and latest_created_at.tzinfo is None:
                latest_created_at = latest_created_at.replace(tzinfo=UTC)
            cooldown = bool(
                latest_created_at is not None
                and (timestamp - latest_created_at).total_seconds() < XP_COOLDOWN_SECONDS
            )

            duplicate = False
            if activity.content_fingerprint:
                duplicate = any(
                    item.content_fingerprint == activity.content_fingerprint for item in recent
                )
            if not duplicate and activity.content_simhash is not None:
                duplicate = any(
                    item.content_simhash is not None
                    and hamming_distance(
                        activity.content_simhash,
                        int(item.content_simhash, 16),
                    )
                    <= 3
                    for item in recent
                )

            base_xp = message_base_xp(activity)
            requested_xp = (
                0 if cooldown or duplicate else adjusted_message_xp(base_xp, len(recent) + 1)
            )
            update = await self._apply_xp(
                session,
                group=group,
                member=member,
                user=user,
                requested_xp=requested_xp,
                timestamp=timestamp,
            )
            author.xp_awarded = update.group_xp_awarded
            return update

    async def award_reaction_xp(
        self,
        *,
        chat_id: int,
        message_id: int,
        positive_delta: int,
        occurred_at: datetime,
    ) -> GamificationUpdate:
        if positive_delta <= 0:
            return GamificationUpdate()
        timestamp = occurred_at.astimezone(UTC)
        async with self._session_factory() as session, session.begin():
            group = await session.get(ChatGroup, chat_id)
            author = await session.get(MessageAuthor, (chat_id, message_id))
            if group is None or author is None:
                return GamificationUpdate()
            member = await session.get(GroupMember, (chat_id, author.telegram_user_id))
            user = await session.get(User, author.telegram_user_id)
            if member is None or user is None:
                return GamificationUpdate()
            return await self._apply_xp(
                session,
                group=group,
                member=member,
                user=user,
                requested_xp=positive_delta * 3,
                timestamp=timestamp,
            )

    async def get_message_author_name(self, chat_id: int, message_id: int) -> str | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GroupMember.display_name)
                .join(
                    MessageAuthor,
                    (MessageAuthor.telegram_chat_id == GroupMember.telegram_chat_id)
                    & (MessageAuthor.telegram_user_id == GroupMember.telegram_user_id),
                )
                .where(
                    MessageAuthor.telegram_chat_id == chat_id,
                    MessageAuthor.message_id == message_id,
                )
                .limit(1)
            )
            value = result.scalar_one_or_none()
            return str(value) if value is not None else None

    async def get_profile(self, chat_id: int, user_id: int) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            group = await session.get(ChatGroup, chat_id)
            member = await session.get(GroupMember, (chat_id, user_id))
            user = await session.get(User, user_id)
            if group is None or member is None or user is None:
                return None
            result = await session.scalars(
                select(MemberAchievement)
                .where(
                    MemberAchievement.telegram_chat_id == chat_id,
                    MemberAchievement.telegram_user_id == user_id,
                )
                .order_by(MemberAchievement.earned_at.asc())
            )
            achievements: list[dict[str, Any]] = []
            for row in result.all():
                definition = ACHIEVEMENT_BY_CODE.get(row.achievement_code)
                achievements.append(
                    {
                        "achievement_code": row.achievement_code,
                        "title": definition.title if definition else row.achievement_code,
                        "earned_at": row.earned_at,
                    }
                )
            local_today = utc_now().astimezone(ZoneInfo(group.timezone)).date()
            month_start = local_today.replace(day=1)
            usage = await session.get(StreakProtectionUsage, (chat_id, user_id, month_start))
            used = usage.used_days if usage else 0
            return {
                "display_name": member.display_name,
                "group_xp_total": member.xp_total,
                "group_level": member.level,
                "global_xp_total": user.global_xp_total,
                "global_level": user.global_level,
                "current_streak": member.current_streak,
                "longest_streak": member.longest_streak,
                "protection_left": max(0, MONTHLY_PROTECTION_DAYS - used),
                "achievements": achievements,
            }

    async def get_comparison(
        self,
        chat_id: int,
        *,
        now: datetime | None = None,
    ) -> tuple[dict[str, int], dict[str, int]]:
        async with self._session_factory() as session:
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                return self._empty_summary(), self._empty_summary()
            local_today = (now or utc_now()).astimezone(ZoneInfo(group.timezone)).date()
            current = await self._summary_between(
                session,
                chat_id,
                local_today - timedelta(days=6),
                local_today,
            )
            previous = await self._summary_between(
                session,
                chat_id,
                local_today - timedelta(days=13),
                local_today - timedelta(days=7),
            )
            return current, previous

    async def get_top_message(
        self,
        chat_id: int,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                return None
            timezone = ZoneInfo(group.timezone)
            local_today = (now or utc_now()).astimezone(timezone).date()
            start_local = datetime.combine(local_today - timedelta(days=6), time.min, timezone)
            end_local = datetime.combine(local_today + timedelta(days=1), time.min, timezone)
            result = await session.execute(
                select(
                    MessageAuthor.message_id,
                    MessageAuthor.reactions_count,
                    GroupMember.display_name,
                )
                .join(
                    GroupMember,
                    (GroupMember.telegram_chat_id == MessageAuthor.telegram_chat_id)
                    & (GroupMember.telegram_user_id == MessageAuthor.telegram_user_id),
                )
                .where(
                    MessageAuthor.telegram_chat_id == chat_id,
                    MessageAuthor.created_at >= start_local.astimezone(UTC),
                    MessageAuthor.created_at < end_local.astimezone(UTC),
                    MessageAuthor.reactions_count > 0,
                )
                .order_by(
                    MessageAuthor.reactions_count.desc(),
                    MessageAuthor.message_id.asc(),
                )
                .limit(1)
            )
            row = result.first()
            if row is None:
                return None
            return {
                "message_id": int(row[0]),
                "reactions_count": int(row[1]),
                "display_name": str(row[2]),
                "url": self.message_link(group, int(row[0])),
            }

    async def get_weekly_achievements(
        self,
        chat_id: int,
        *,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                return []
            timezone = ZoneInfo(group.timezone)
            local_today = (now or utc_now()).astimezone(timezone).date()
            start_local = datetime.combine(local_today - timedelta(days=6), time.min, timezone)
            result = await session.execute(
                select(
                    MemberAchievement.achievement_code,
                    MemberAchievement.earned_at,
                    GroupMember.display_name,
                )
                .join(
                    GroupMember,
                    (GroupMember.telegram_chat_id == MemberAchievement.telegram_chat_id)
                    & (GroupMember.telegram_user_id == MemberAchievement.telegram_user_id),
                )
                .where(
                    MemberAchievement.telegram_chat_id == chat_id,
                    MemberAchievement.earned_at >= start_local.astimezone(UTC),
                )
                .order_by(MemberAchievement.earned_at.desc())
                .limit(12)
            )
            items: list[dict[str, Any]] = []
            for code, earned_at, display_name in result.all():
                definition = ACHIEVEMENT_BY_CODE.get(str(code))
                items.append(
                    {
                        "code": str(code),
                        "title": definition.title if definition else str(code),
                        "display_name": str(display_name),
                        "earned_at": earned_at,
                    }
                )
            return items

    @staticmethod
    def message_link(group: ChatGroup | dict[str, Any], message_id: int) -> str | None:
        username = group.username if isinstance(group, ChatGroup) else group.get("username")
        chat_id = (
            group.telegram_chat_id
            if isinstance(group, ChatGroup)
            else int(group["telegram_chat_id"])
        )
        if username:
            return f"https://t.me/{str(username).lstrip('@')}/{message_id}"
        raw_chat_id = str(abs(chat_id))
        if raw_chat_id.startswith("100"):
            return f"https://t.me/c/{raw_chat_id[3:]}/{message_id}"
        return None

    async def _apply_xp(
        self,
        session: AsyncSession,
        *,
        group: ChatGroup,
        member: GroupMember,
        user: User,
        requested_xp: int,
        timestamp: datetime,
    ) -> GamificationUpdate:
        old_group_level = member.level
        old_global_level = user.global_level
        local_date = timestamp.astimezone(ZoneInfo(group.timezone)).date()
        daily = await session.get(
            DailyActivity,
            (group.telegram_chat_id, member.telegram_user_id, local_date),
        )
        if daily is None:
            daily = DailyActivity(
                telegram_chat_id=group.telegram_chat_id,
                telegram_user_id=member.telegram_user_id,
                activity_date=local_date,
                messages_count=0,
                media_count=0,
                replies_count=0,
                reactions_received=0,
                photo_count=0,
                voice_count=0,
                night_messages_count=0,
                morning_messages_count=0,
                xp_earned=0,
            )
            session.add(daily)
            await session.flush()

        previous_daily_xp = daily.xp_earned
        group_award = min(
            max(0, requested_xp),
            max(0, GROUP_DAILY_XP_CAP - daily.xp_earned),
        )
        global_date = timestamp.date()
        global_daily = await session.get(GlobalDailyXP, (user.telegram_id, global_date))
        if global_daily is None:
            global_daily = GlobalDailyXP(
                telegram_user_id=user.telegram_id,
                activity_date=global_date,
                xp_earned=0,
            )
            session.add(global_daily)
            await session.flush()
        global_award = min(
            group_award,
            max(0, GLOBAL_DAILY_XP_CAP - global_daily.xp_earned),
        )

        if group_award:
            daily.xp_earned += group_award
            member.xp_total += group_award
            member.level = level_for_xp(member.xp_total)
        if global_award:
            global_daily.xp_earned += global_award
            user.global_xp_total += global_award
            user.global_level = level_for_xp(user.global_xp_total)

        if previous_daily_xp < STREAK_XP_THRESHOLD <= daily.xp_earned:
            await self._advance_streak(session, group, member, local_date)

        achievements = await self._award_new_achievements(session, member, timestamp)
        return GamificationUpdate(
            group_xp_awarded=group_award,
            global_xp_awarded=global_award,
            old_group_level=old_group_level,
            new_group_level=member.level,
            old_global_level=old_global_level,
            new_global_level=user.global_level,
            current_streak=member.current_streak,
            achievements=tuple(achievements),
        )

    async def _advance_streak(
        self,
        session: AsyncSession,
        group: ChatGroup,
        member: GroupMember,
        active_date: date,
    ) -> None:
        previous = member.last_streak_date
        if previous is None:
            member.current_streak = 1
        elif active_date <= previous:
            return
        else:
            missing_dates = [
                previous + timedelta(days=offset)
                for offset in range(1, (active_date - previous).days)
            ]
            protected = await self._consume_protections(
                session,
                group.telegram_chat_id,
                member.telegram_user_id,
                missing_dates,
            )
            member.current_streak = member.current_streak + 1 if protected else 1
        member.longest_streak = max(member.longest_streak, member.current_streak)
        member.last_streak_date = active_date

    async def _consume_protections(
        self,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        missing_dates: list[date],
    ) -> bool:
        if not missing_dates:
            return True
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
            if usage.used_days + needed > MONTHLY_PROTECTION_DAYS:
                return False
            usages[month_start] = usage
        for month_start, needed in required.items():
            usages[month_start].used_days += needed
        return True

    async def _award_new_achievements(
        self,
        session: AsyncSession,
        member: GroupMember,
        timestamp: datetime,
    ) -> list[AchievementEarned]:
        result = await session.scalars(
            select(MemberAchievement.achievement_code).where(
                MemberAchievement.telegram_chat_id == member.telegram_chat_id,
                MemberAchievement.telegram_user_id == member.telegram_user_id,
            )
        )
        existing = set(result.all())
        stats = {
            "xp_total": member.xp_total,
            "level": member.level,
            "messages_count": member.messages_count,
            "reactions_received": member.reactions_received,
            "replies_count": member.replies_count,
            "photo_count": member.photo_count,
            "voice_count": member.voice_count,
            "current_streak": member.current_streak,
        }
        earned = evaluate_achievements(stats, existing)
        for item in earned:
            session.add(
                MemberAchievement(
                    telegram_chat_id=member.telegram_chat_id,
                    telegram_user_id=member.telegram_user_id,
                    achievement_code=item.code,
                    earned_at=timestamp,
                )
            )
        return earned

    async def _summary_between(
        self,
        session: AsyncSession,
        chat_id: int,
        start_date: date,
        end_date: date,
    ) -> dict[str, int]:
        result = await session.scalars(
            select(DailyActivity).where(
                DailyActivity.telegram_chat_id == chat_id,
                DailyActivity.activity_date >= start_date,
                DailyActivity.activity_date <= end_date,
            )
        )
        rows: Sequence[DailyActivity] = result.all()
        summary = self._empty_summary()
        active_users: set[int] = set()
        for row in rows:
            if any(int(getattr(row, field)) for field in SUMMARY_FIELDS if field != "xp_earned"):
                active_users.add(row.telegram_user_id)
            for field in SUMMARY_FIELDS:
                summary[field] += int(getattr(row, field))
        summary["active_members"] = len(active_users)
        return summary

    @staticmethod
    def _empty_summary() -> dict[str, int]:
        return {**{field: 0 for field in SUMMARY_FIELDS}, "active_members": 0}
