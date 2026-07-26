from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.achievement_models import AchievementUnlockRecord
from app.achievements.catalog import ACHIEVEMENTS as CANONICAL_ACHIEVEMENTS
from app.achievements.presentation import achievement_progress_payload
from app.models import (
    ChatGroup,
    DailyActivity,
    DailyReactionEmoji,
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
    ACHIEVEMENTS,
    MONTHLY_PROTECTION_DAYS,
    level_progress,
    level_tier,
)
from app.services.miniapp import message_link, percentage_change
from app.services.nominations import METRICS

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


class MiniAppAnalyticsMixin:
    async def _group_activity_series(
        self,
        session: AsyncSession,
        group: ChatGroup,
        start: date | None,
        end: date | None,
        current: datetime,
    ) -> list[dict[str, Any]]:
        local_today = current.astimezone(ZoneInfo(group.timezone)).date()
        chart_start = start or local_today - timedelta(days=29)
        chart_end = end or local_today
        result = await session.execute(
            select(
                DailyActivity.activity_date,
                func.coalesce(func.sum(DailyActivity.messages_count), 0),
                func.coalesce(func.sum(DailyActivity.reactions_received), 0),
                func.coalesce(func.sum(DailyActivity.replies_count), 0),
                func.coalesce(func.sum(DailyActivity.xp_earned), 0),
            )
            .where(
                DailyActivity.telegram_chat_id == group.telegram_chat_id,
                DailyActivity.activity_date >= chart_start,
                DailyActivity.activity_date <= chart_end,
            )
            .group_by(DailyActivity.activity_date)
            .order_by(DailyActivity.activity_date)
        )
        return [
            {
                "date": row[0].isoformat(),
                "messages": int(row[1]),
                "reactions": int(row[2]),
                "replies": int(row[3]),
                "xp": int(row[4]),
            }
            for row in result.all()
        ]

    async def _heatmap(
        self,
        session: AsyncSession,
        group: ChatGroup,
        start: date | None,
        end: date | None,
        current: datetime,
    ) -> list[dict[str, Any]]:
        local_today = current.astimezone(ZoneInfo(group.timezone)).date()
        heatmap_start = start or local_today - timedelta(days=29)
        heatmap_end = end or local_today
        result = await session.execute(
            select(
                DailyActivity.activity_date,
                func.coalesce(func.sum(DailyActivity.messages_count), 0),
                func.coalesce(func.sum(DailyActivity.night_messages_count), 0),
                func.coalesce(func.sum(DailyActivity.morning_messages_count), 0),
            )
            .where(
                DailyActivity.telegram_chat_id == group.telegram_chat_id,
                DailyActivity.activity_date >= heatmap_start,
                DailyActivity.activity_date <= heatmap_end,
            )
            .group_by(DailyActivity.activity_date)
        )
        buckets: dict[tuple[int, str], int] = {}
        for activity_date, total, night, morning in result.all():
            day = int(activity_date.weekday())
            buckets[(day, "night")] = buckets.get((day, "night"), 0) + int(night)
            buckets[(day, "morning")] = buckets.get((day, "morning"), 0) + int(morning)
            daytime = max(0, int(total) - int(night) - int(morning))
            buckets[(day, "day")] = buckets.get((day, "day"), 0) + daytime
        return [
            {"weekday": weekday, "bucket": bucket, "value": buckets.get((weekday, bucket), 0)}
            for weekday in range(7)
            for bucket in ("night", "morning", "day")
        ]

    async def _top_message(
        self,
        session: AsyncSession,
        group: ChatGroup,
        start: date | None,
        end: date | None,
    ) -> dict[str, Any] | None:
        query = (
            select(
                MessageAuthor.message_id,
                MessageAuthor.reactions_count,
                MessageAuthor.created_at,
                GroupMember.display_name,
            )
            .join(
                GroupMember,
                (GroupMember.telegram_chat_id == MessageAuthor.telegram_chat_id)
                & (GroupMember.telegram_user_id == MessageAuthor.telegram_user_id),
            )
            .where(
                MessageAuthor.telegram_chat_id == group.telegram_chat_id,
                MessageAuthor.reactions_count > 0,
            )
        )
        if start is not None and end is not None:
            timezone = ZoneInfo(group.timezone)
            start_at = datetime.combine(start, datetime.min.time(), timezone).astimezone(UTC)
            end_at = datetime.combine(
                end + timedelta(days=1),
                datetime.min.time(),
                timezone,
            ).astimezone(UTC)
            query = query.where(
                MessageAuthor.created_at >= start_at,
                MessageAuthor.created_at < end_at,
            )
        row = (
            await session.execute(
                query.order_by(
                    MessageAuthor.reactions_count.desc(),
                    MessageAuthor.message_id.asc(),
                ).limit(1)
            )
        ).first()
        if row is None:
            return None
        return {
            "message_id": int(row[0]),
            "reactions_count": int(row[1]),
            "created_at": row[2].isoformat(),
            "display_name": row[3],
            "url": message_link(
                int(group.telegram_chat_id),
                group.username,
                int(row[0]),
            ),
        }

    async def _popular_reaction(
        self,
        session: AsyncSession,
        group: ChatGroup,
        start: date | None,
        end: date | None,
    ) -> dict[str, Any] | None:
        query = select(
            DailyReactionEmoji.emoji_key,
            func.coalesce(func.sum(DailyReactionEmoji.reactions_count), 0),
        ).where(DailyReactionEmoji.telegram_chat_id == group.telegram_chat_id)
        if start is not None and end is not None:
            query = query.where(
                DailyReactionEmoji.activity_date >= start,
                DailyReactionEmoji.activity_date <= end,
            )
        row = (
            await session.execute(
                query.group_by(DailyReactionEmoji.emoji_key)
                .order_by(func.sum(DailyReactionEmoji.reactions_count).desc())
                .limit(1)
            )
        ).first()
        if row is None or int(row[1]) <= 0:
            return None
        return {"emoji": str(row[0]), "count": int(row[1])}

    async def get_premium_analytics(
        self,
        user_id: int,
        chat_id: int,
        period: PremiumAnalyticsPeriod,
        *,
        compare: PremiumAnalyticsPeriod | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        current = (now or utc_now()).astimezone(UTC)
        async with self._session_factory() as session:
            access = await self._membership(session, user_id, chat_id)
            if access is None:
                return None
            group, _member = access
            today = current.astimezone(ZoneInfo(group.timezone)).date()

            async def range_payload(selected: PremiumAnalyticsPeriod) -> dict[str, Any]:
                days = PREMIUM_PERIOD_DAYS[selected]
                start = today - timedelta(days=days - 1)
                overview = await self._summary(session, chat_id, start, today)
                activity_series = await self._group_activity_series(
                    session,
                    group,
                    start,
                    today,
                    current,
                )
                return {
                    "period": selected,
                    "days": days,
                    "start": start.isoformat(),
                    "end": today.isoformat(),
                    "overview": overview,
                    "activity_series": activity_series,
                }

            selected_payload = await range_payload(period)
            comparison_payload = await range_payload(compare) if compare else None
            trends = {
                key: percentage_change(
                    int(selected_payload["overview"][key]),
                    int(comparison_payload["overview"][key]),
                )
                if comparison_payload
                else None
                for key in selected_payload["overview"]
            }
            return {
                "group": self._serialize_group(group),
                **selected_payload,
                "comparison": comparison_payload,
                "trends": trends,
            }

    async def get_year_summary(self, user_id: int, year: int) -> dict[str, Any] | None:
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        async with self._session_factory() as session:
            user = await session.get(User, user_id)
            if user is None:
                return None

            memberships = await self._memberships(session, user_id)
            rows = (
                await session.execute(
                    select(
                        DailyActivity.activity_date,
                        DailyActivity.messages_count,
                        DailyActivity.xp_earned,
                    ).where(
                        DailyActivity.telegram_user_id == user_id,
                        DailyActivity.activity_date >= start,
                        DailyActivity.activity_date <= end,
                    )
                )
            ).all()

            messages_count = sum(int(row.messages_count or 0) for row in rows)
            xp_earned = sum(int(row.xp_earned or 0) for row in rows)
            active_days = len(
                {
                    row.activity_date
                    for row in rows
                    if int(row.messages_count or 0) > 0 or int(row.xp_earned or 0) > 0
                }
            )
            monthly_xp: dict[int, int] = {}
            for row in rows:
                month = int(row.activity_date.month)
                monthly_xp[month] = monthly_xp.get(month, 0) + int(row.xp_earned or 0)

            top_month = (
                max(monthly_xp, key=lambda month: (monthly_xp[month], -month))
                if monthly_xp
                else None
            )
            best_streak = max(
                (int(member.longest_streak) for _group, member in memberships),
                default=0,
            )
            achievements_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(AchievementUnlockRecord)
                    .where(
                        AchievementUnlockRecord.telegram_user_id == user_id,
                        AchievementUnlockRecord.earned_at >= datetime(year, 1, 1, tzinfo=UTC),
                        AchievementUnlockRecord.earned_at < datetime(year + 1, 1, 1, tzinfo=UTC),
                    )
                )
                or 0
            )
            return {
                "year": year,
                "messages_count": messages_count,
                "xp_earned": xp_earned,
                "active_days": active_days,
                "groups_count": len(memberships),
                "best_streak": best_streak,
                "top_month": top_month,
                "monthly_xp": [
                    {"month": month, "xp": monthly_xp.get(month, 0)} for month in range(1, 13)
                ],
                "achievements_count": achievements_count,
            }
