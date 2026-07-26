from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.domain import StatsPeriod
from app.models import (
    ChatGroup,
    DailyActivity,
    DailyReactionEmoji,
    GroupMember,
    utc_now,
)

MemberStats = dict[str, Any]
GroupSummary = dict[str, int]
GroupSettings = dict[str, Any]

COUNTER_FIELDS = (
    "messages_count",
    "media_count",
    "replies_count",
    "reactions_received",
    "photo_count",
    "voice_count",
    "night_messages_count",
    "morning_messages_count",
)


def _period_start(period: StatsPeriod, today: date) -> date | None:
    if period == "today":
        return today
    if period == "week":
        return today - timedelta(days=6)
    if period == "month":
        return today.replace(day=1)
    return None


class ActivityQueriesMixin:
    async def get_member_stats(
        self,
        chat_id: int,
        user_id: int,
        period: StatsPeriod = "all",
        *,
        now: datetime | None = None,
    ) -> MemberStats | None:
        members = await self.get_period_members(chat_id, period, now=now)
        return next((item for item in members if item["telegram_user_id"] == user_id), None)

    async def get_group_summary(
        self,
        chat_id: int,
        period: StatsPeriod = "all",
        *,
        now: datetime | None = None,
    ) -> GroupSummary:
        members = await self.get_period_members(chat_id, period, now=now)
        summary: GroupSummary = {field: 0 for field in COUNTER_FIELDS}
        for member in members:
            for field in COUNTER_FIELDS:
                summary[field] += int(member[field])
        summary["active_members"] = len(
            [member for member in members if any(int(member[field]) for field in COUNTER_FIELDS)]
        )
        return summary

    async def get_top_members(
        self,
        chat_id: int,
        *,
        limit: int = 10,
        period: StatsPeriod = "all",
        now: datetime | None = None,
    ) -> list[MemberStats]:
        members = await self.get_period_members(chat_id, period, now=now)
        members.sort(
            key=lambda item: (
                -int(item["messages_count"]),
                -int(item["reactions_received"]),
                -int(item["replies_count"]),
                str(item["display_name"]).lower(),
            )
        )
        return members[:limit]

    async def get_period_members(
        self,
        chat_id: int,
        period: StatsPeriod,
        *,
        now: datetime | None = None,
    ) -> list[MemberStats]:
        async with self._session_factory() as session:
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                return []

            if period == "all":
                result = await session.scalars(
                    select(GroupMember).where(GroupMember.telegram_chat_id == chat_id)
                )
                rows: Sequence[GroupMember] = result.all()
                return [self._serialize_member(row) for row in rows]

            current = (now or utc_now()).astimezone(ZoneInfo(group.timezone))
            start_date = _period_start(period, current.date())
            assert start_date is not None
            result = await session.execute(
                select(
                    GroupMember.telegram_user_id,
                    GroupMember.display_name,
                    GroupMember.username,
                    *[
                        func.coalesce(func.sum(getattr(DailyActivity, field)), 0)
                        for field in COUNTER_FIELDS
                    ],
                )
                .join(
                    DailyActivity,
                    (DailyActivity.telegram_chat_id == GroupMember.telegram_chat_id)
                    & (DailyActivity.telegram_user_id == GroupMember.telegram_user_id),
                )
                .where(
                    GroupMember.telegram_chat_id == chat_id,
                    DailyActivity.activity_date >= start_date,
                    DailyActivity.activity_date <= current.date(),
                )
                .group_by(
                    GroupMember.telegram_user_id,
                    GroupMember.display_name,
                    GroupMember.username,
                )
            )
            members: list[MemberStats] = []
            for row in result.all():
                item: MemberStats = {
                    "telegram_user_id": int(row[0]),
                    "display_name": row[1],
                    "username": row[2],
                }
                for index, field in enumerate(COUNTER_FIELDS, start=3):
                    item[field] = int(row[index])
                members.append(item)
            return members

    async def get_popular_reaction(
        self,
        chat_id: int,
        period: StatsPeriod = "week",
        *,
        now: datetime | None = None,
    ) -> tuple[str, int] | None:
        async with self._session_factory() as session:
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                return None
            query = select(
                DailyReactionEmoji.emoji_key,
                func.sum(DailyReactionEmoji.reactions_count).label("count"),
            ).where(DailyReactionEmoji.telegram_chat_id == chat_id)
            if period != "all":
                current = (now or utc_now()).astimezone(ZoneInfo(group.timezone))
                start_date = _period_start(period, current.date())
                query = query.where(
                    DailyReactionEmoji.activity_date >= start_date,
                    DailyReactionEmoji.activity_date <= current.date(),
                )
            result = await session.execute(
                query.group_by(DailyReactionEmoji.emoji_key)
                .order_by(func.sum(DailyReactionEmoji.reactions_count).desc())
                .limit(1)
            )
            row = result.first()
            if row is None or int(row[1]) <= 0:
                return None
            return str(row[0]), int(row[1])

    async def list_due_weekly_reports(self, *, now: datetime | None = None) -> list[GroupSettings]:
        current_utc = (now or utc_now()).astimezone(UTC)
        async with self._session_factory() as session:
            result = await session.scalars(
                select(ChatGroup).where(
                    ChatGroup.is_active.is_(True),
                    ChatGroup.is_paused.is_(False),
                    ChatGroup.weekly_reports_enabled.is_(True),
                )
            )
            due: list[GroupSettings] = []
            for group in result.all():
                local_now = current_utc.astimezone(ZoneInfo(group.timezone))
                scheduled = local_now.replace(
                    hour=group.report_hour,
                    minute=group.report_minute,
                    second=0,
                    microsecond=0,
                )
                if local_now.weekday() != group.report_weekday or local_now < scheduled:
                    continue
                if group.last_weekly_report_at is not None:
                    last_local = group.last_weekly_report_at.astimezone(ZoneInfo(group.timezone))
                    if last_local.date() == local_now.date():
                        continue
                due.append(self._serialize_group(group))
            return due

    async def mark_weekly_report_sent(
        self, chat_id: int, *, sent_at: datetime | None = None
    ) -> None:
        async with self._session_factory() as session, session.begin():
            group = await session.get(ChatGroup, chat_id)
            if group is not None:
                group.last_weekly_report_at = (sent_at or utc_now()).astimezone(UTC)
                group.updated_at = utc_now()
