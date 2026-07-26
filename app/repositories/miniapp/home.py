from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ChatGroup,
    DailyActivity,
    GlobalDailyXP,
    GroupMember,
    MemberAchievement,
    User,
    utc_now,
)
from app.services.gamification import (
    ACHIEVEMENT_BY_CODE,
    MONTHLY_PROTECTION_DAYS,
    level_progress,
    level_tier,
)
from app.services.miniapp import percentage_change

MiniAppPeriod = Literal["week", "month", "all"]
RankingMetric = Literal["xp", "messages", "reactions", "replies", "streak"]
PremiumAnalyticsPeriod = Literal["quarter", "half_year", "year"]
PREMIUM_PERIOD_DAYS: dict[PremiumAnalyticsPeriod, int] = {
    "quarter": 90,
    "half_year": 180,
    "year": 365,
}

SUMMARY_FIELDS = (
    "messages_count",
    "media_count",
    "replies_count",
    "reactions_received",
    "photo_count",
    "voice_count",
    "night_messages_count",
    "morning_messages_count",
)


class MiniAppHomeMixin:
    async def get_home(
        self,
        user_id: int,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        current = (now or utc_now()).astimezone(UTC)
        today = current.date()
        async with self._session_factory() as session:
            user = await session.get(User, user_id)
            if user is None:
                return None

            memberships = await self._memberships(session, user_id)
            groups = [
                await self._group_card(session, group, member, current)
                for group, member in memberships
            ]
            groups.sort(
                key=lambda item: (
                    -int(item["period"]["xp_earned"]),
                    str(item["title"]).casefold(),
                )
            )

            rank = (
                int(
                    await session.scalar(
                        select(func.count())
                        .select_from(User)
                        .where(User.global_xp_total > user.global_xp_total)
                    )
                    or 0
                )
                + 1
            )
            total_users = int(await session.scalar(select(func.count()).select_from(User)) or 0)
            daily_global = await session.get(GlobalDailyXP, (user_id, today))
            activity_series = await self._global_activity_series(session, user_id, today)
            recent_achievements = await self._recent_achievements(session, user_id)
            protection_values = [
                await self._protection_left(session, group, user_id, current)
                for group, _member in memberships
            ]
            current_streak = max(
                (int(member.current_streak) for _group, member in memberships),
                default=0,
            )
            longest_streak = max(
                (int(member.longest_streak) for _group, member in memberships),
                default=0,
            )
            level, progress, needed = level_progress(int(user.global_xp_total))

            return {
                "user": {
                    "telegram_id": int(user.telegram_id),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "display_name": " ".join(
                        value for value in (user.first_name, user.last_name) if value
                    ),
                    "username": user.username,
                },
                "global_progress": {
                    "xp_total": int(user.global_xp_total),
                    "level": level,
                    "tier": level_tier(level),
                    "progress": progress,
                    "needed": needed,
                    "rank": rank,
                    "total_users": total_users,
                    "percentile": self._percentile(rank, total_users),
                },
                "quick_stats": {
                    "xp_today": int(daily_global.xp_earned) if daily_global else 0,
                    "current_streak": current_streak,
                    "longest_streak": longest_streak,
                    "protection_left": min(protection_values, default=MONTHLY_PROTECTION_DAYS),
                    "groups_count": len(groups),
                    "messages_7d": sum(int(item["period"]["messages_count"]) for item in groups),
                },
                "activity_series": activity_series,
                "recent_achievements": recent_achievements,
                "groups": groups[:6],
            }

    async def list_groups(
        self,
        user_id: int,
        *,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        current = (now or utc_now()).astimezone(UTC)
        async with self._session_factory() as session:
            memberships = await self._memberships(session, user_id)
            result = [
                await self._group_card(session, group, member, current)
                for group, member in memberships
            ]
            result.sort(
                key=lambda item: (
                    -int(item["period"]["xp_earned"]),
                    str(item["title"]).casefold(),
                )
            )
            return result

    async def _group_card(
        self,
        session: AsyncSession,
        group: ChatGroup,
        member: GroupMember,
        current: datetime,
    ) -> dict[str, Any]:
        today = current.astimezone(ZoneInfo(group.timezone)).date()
        period = await self._summary(
            session,
            int(group.telegram_chat_id),
            today - timedelta(days=6),
            today,
            user_id=int(member.telegram_user_id),
        )
        previous = await self._summary(
            session,
            int(group.telegram_chat_id),
            today - timedelta(days=13),
            today - timedelta(days=7),
            user_id=int(member.telegram_user_id),
        )
        rankings = await self._rankings_in_session(
            session,
            int(member.telegram_user_id),
            group,
            "xp",
            "all",
            current,
        )
        return {
            "telegram_chat_id": int(group.telegram_chat_id),
            "title": group.title,
            "username": group.username,
            "initials": self._initials(group.title),
            "level": int(member.level),
            "xp_total": int(member.xp_total),
            "current_streak": int(member.current_streak),
            "rank": self._row_rank(rankings["rows"], int(member.telegram_user_id)),
            "period": period,
            "trend": percentage_change(
                int(period["xp_earned"]),
                int(previous["xp_earned"]),
            ),
            "is_admin": False,
            "last_activity_at": member.last_seen_at.isoformat(),
        }

    async def _global_activity_series(
        self,
        session: AsyncSession,
        user_id: int,
        today: date,
    ) -> list[dict[str, Any]]:
        start = today - timedelta(days=6)
        result = await session.execute(
            select(
                DailyActivity.activity_date,
                func.coalesce(func.sum(DailyActivity.xp_earned), 0),
                func.coalesce(func.sum(DailyActivity.messages_count), 0),
                func.coalesce(func.sum(DailyActivity.reactions_received), 0),
            )
            .where(
                DailyActivity.telegram_user_id == user_id,
                DailyActivity.activity_date >= start,
                DailyActivity.activity_date <= today,
            )
            .group_by(DailyActivity.activity_date)
        )
        values = {row[0]: row for row in result.all()}
        return [
            {
                "date": day.isoformat(),
                "xp": int(values[day][1]) if day in values else 0,
                "messages": int(values[day][2]) if day in values else 0,
                "reactions": int(values[day][3]) if day in values else 0,
            }
            for day in (start + timedelta(days=index) for index in range(7))
        ]

    async def _recent_achievements(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> list[dict[str, Any]]:
        result = await session.execute(
            select(MemberAchievement, ChatGroup.title)
            .join(
                ChatGroup,
                ChatGroup.telegram_chat_id == MemberAchievement.telegram_chat_id,
            )
            .where(MemberAchievement.telegram_user_id == user_id)
            .order_by(MemberAchievement.earned_at.desc())
            .limit(3)
        )
        items: list[dict[str, Any]] = []
        for row in result.all():
            achievement = row.MemberAchievement
            definition = ACHIEVEMENT_BY_CODE.get(achievement.achievement_code)
            items.append(
                {
                    "code": achievement.achievement_code,
                    "title": definition.title if definition else achievement.achievement_code,
                    "description": definition.description if definition else "",
                    "rarity": "epic" if definition and definition.important else "common",
                    "earned_at": achievement.earned_at.isoformat(),
                    "group_title": row.title,
                }
            )
        return items
