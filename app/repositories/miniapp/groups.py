from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ChatGroup,
    DailyActivity,
    GroupMember,
    utc_now,
)
from app.services.gamification import (
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


class MiniAppGroupsMixin:
    async def get_group_dashboard(
        self,
        user_id: int,
        chat_id: int,
        period: MiniAppPeriod,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        current = (now or utc_now()).astimezone(UTC)
        async with self._session_factory() as session:
            access = await self._membership(session, user_id, chat_id)
            if access is None:
                return None
            group, member = access
            start, end, previous_start, previous_end = self._period_bounds(
                group,
                period,
                current,
            )
            summary = await self._summary(session, chat_id, start, end)
            previous = (
                await self._summary(session, chat_id, previous_start, previous_end)
                if previous_start is not None
                else self._empty_summary()
            )
            personal_summary = await self._summary(
                session,
                chat_id,
                start,
                end,
                user_id=user_id,
            )
            rankings = await self._rankings_in_session(
                session,
                user_id,
                group,
                "xp",
                period,
                current,
            )
            period_members = await self._period_members(session, group, period, current)
            nominations = self._nominations(period_members)
            top_message = await self._top_message(session, group, start, end)
            popular_reaction = await self._popular_reaction(session, group, start, end)
            level, progress, needed = level_progress(int(member.xp_total))
            protection_left = await self._protection_left(session, group, user_id, current)

            trends = {
                field: percentage_change(int(summary[field]), int(previous[field]))
                for field in (*SUMMARY_FIELDS, "xp_earned", "active_members")
            }
            return {
                "group": self._serialize_group(group),
                "period": period,
                "overview": {
                    "current": summary,
                    "previous": previous,
                    "trends": trends,
                },
                "activity_series": await self._group_activity_series(
                    session,
                    group,
                    start,
                    end,
                    current,
                ),
                "heatmap": await self._heatmap(session, group, start, end, current),
                "personal_progress": {
                    "xp_total": int(member.xp_total),
                    "level": level,
                    "tier": level_tier(level),
                    "progress": progress,
                    "needed": needed,
                    "current_streak": int(member.current_streak),
                    "longest_streak": int(member.longest_streak),
                    "protection_left": protection_left,
                    "period": personal_summary,
                    "rank": self._row_rank(rankings["rows"], user_id),
                },
                "leaderboard": rankings["rows"][:10],
                "current_user_rank": rankings["current_user"],
                "top_message": top_message,
                "popular_reaction": popular_reaction,
                "nominations": nominations,
                "settings": self._serialize_settings(group),
            }

    async def get_rankings(
        self,
        user_id: int,
        chat_id: int,
        metric: RankingMetric,
        period: MiniAppPeriod,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        current = (now or utc_now()).astimezone(UTC)
        async with self._session_factory() as session:
            access = await self._membership(session, user_id, chat_id)
            if access is None:
                return None
            group, _member = access
            return await self._rankings_in_session(
                session,
                user_id,
                group,
                metric,
                period,
                current,
            )

    async def _summary(
        self,
        session: AsyncSession,
        chat_id: int,
        start: date | None,
        end: date | None,
        *,
        user_id: int | None = None,
    ) -> dict[str, int]:
        if start is None or end is None:
            expressions = [
                func.coalesce(func.sum(getattr(GroupMember, field)), 0) for field in SUMMARY_FIELDS
            ]
            query = select(
                *expressions,
                func.coalesce(func.sum(GroupMember.xp_total), 0),
                func.count(GroupMember.telegram_user_id),
            ).where(GroupMember.telegram_chat_id == chat_id)
            if user_id is not None:
                query = query.where(GroupMember.telegram_user_id == user_id)
            row = (await session.execute(query)).one()
        else:
            expressions = [
                func.coalesce(func.sum(getattr(DailyActivity, field)), 0)
                for field in SUMMARY_FIELDS
            ]
            query = select(
                *expressions,
                func.coalesce(func.sum(DailyActivity.xp_earned), 0),
                func.count(func.distinct(DailyActivity.telegram_user_id)),
            ).where(
                DailyActivity.telegram_chat_id == chat_id,
                DailyActivity.activity_date >= start,
                DailyActivity.activity_date <= end,
            )
            if user_id is not None:
                query = query.where(DailyActivity.telegram_user_id == user_id)
            row = (await session.execute(query)).one()

        result = {field: int(row[index]) for index, field in enumerate(SUMMARY_FIELDS)}
        result["xp_earned"] = int(row[len(SUMMARY_FIELDS)])
        result["active_members"] = int(row[len(SUMMARY_FIELDS) + 1])
        return result

    async def _period_members(
        self,
        session: AsyncSession,
        group: ChatGroup,
        period: MiniAppPeriod,
        current: datetime,
    ) -> list[dict[str, Any]]:
        start, end, _previous_start, _previous_end = self._period_bounds(
            group,
            period,
            current,
        )
        if start is None:
            rows = (
                await session.scalars(
                    select(GroupMember).where(
                        GroupMember.telegram_chat_id == group.telegram_chat_id
                    )
                )
            ).all()
            return [self._member_totals(row) for row in rows]

        result = await session.execute(
            select(
                GroupMember.telegram_user_id,
                GroupMember.display_name,
                GroupMember.username,
                *[
                    func.coalesce(func.sum(getattr(DailyActivity, field)), 0)
                    for field in SUMMARY_FIELDS
                ],
                func.coalesce(func.sum(DailyActivity.xp_earned), 0),
                GroupMember.current_streak,
            )
            .join(
                DailyActivity,
                (DailyActivity.telegram_chat_id == GroupMember.telegram_chat_id)
                & (DailyActivity.telegram_user_id == GroupMember.telegram_user_id),
            )
            .where(
                GroupMember.telegram_chat_id == group.telegram_chat_id,
                DailyActivity.activity_date >= start,
                DailyActivity.activity_date <= end,
            )
            .group_by(
                GroupMember.telegram_user_id,
                GroupMember.display_name,
                GroupMember.username,
                GroupMember.current_streak,
            )
        )
        items: list[dict[str, Any]] = []
        for row in result.all():
            item = {
                "telegram_user_id": int(row[0]),
                "display_name": row[1],
                "username": row[2],
            }
            for index, field in enumerate(SUMMARY_FIELDS, start=3):
                item[field] = int(row[index])
            item["xp_earned"] = int(row[3 + len(SUMMARY_FIELDS)])
            item["current_streak"] = int(row[4 + len(SUMMARY_FIELDS)])
            items.append(item)
        return items

    async def _rankings_in_session(
        self,
        session: AsyncSession,
        user_id: int,
        group: ChatGroup,
        metric: RankingMetric,
        period: MiniAppPeriod,
        current: datetime,
    ) -> dict[str, Any]:
        members = await self._period_members(session, group, period, current)
        metric_field = {
            "xp": "xp_earned" if period != "all" else "xp_total",
            "messages": "messages_count",
            "reactions": "reactions_received",
            "replies": "replies_count",
            "streak": "current_streak",
        }[metric]
        members.sort(
            key=lambda item: (
                -int(item.get(metric_field, 0)),
                str(item["display_name"]).casefold(),
            )
        )
        rows: list[dict[str, Any]] = []
        current_user: dict[str, Any] | None = None
        for rank, item in enumerate(members, start=1):
            row = {
                "rank": rank,
                "telegram_user_id": int(item["telegram_user_id"]),
                "display_name": item["display_name"],
                "username": item.get("username"),
                "value": int(item.get(metric_field, 0)),
                "metric": metric,
                "is_current_user": int(item["telegram_user_id"]) == user_id,
            }
            if row["is_current_user"]:
                current_user = row
            if rank <= 50:
                rows.append(row)
        return {
            "metric": metric,
            "period": period,
            "rows": rows,
            "current_user": current_user,
        }
