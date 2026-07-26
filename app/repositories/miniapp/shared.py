from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    ChatGroup,
    GroupMember,
)
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


class MiniAppShared:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def _memberships(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> list[tuple[ChatGroup, GroupMember]]:
        result = await session.execute(
            select(ChatGroup, GroupMember)
            .join(
                GroupMember,
                GroupMember.telegram_chat_id == ChatGroup.telegram_chat_id,
            )
            .where(
                GroupMember.telegram_user_id == user_id,
                ChatGroup.is_active.is_(True),
            )
        )
        return [(row.ChatGroup, row.GroupMember) for row in result.all()]

    async def _membership(
        self,
        session: AsyncSession,
        user_id: int,
        chat_id: int,
    ) -> tuple[ChatGroup, GroupMember] | None:
        result = await session.execute(
            select(ChatGroup, GroupMember)
            .join(
                GroupMember,
                GroupMember.telegram_chat_id == ChatGroup.telegram_chat_id,
            )
            .where(
                ChatGroup.telegram_chat_id == chat_id,
                ChatGroup.is_active.is_(True),
                GroupMember.telegram_user_id == user_id,
            )
            .limit(1)
        )
        row = result.first()
        return (row.ChatGroup, row.GroupMember) if row else None

    def _period_bounds(
        self,
        group: ChatGroup,
        period: MiniAppPeriod,
        current: datetime,
    ) -> tuple[date | None, date | None, date | None, date | None]:
        today = current.astimezone(ZoneInfo(group.timezone)).date()
        if period == "all":
            return None, None, None, None
        days = 7 if period == "week" else 30
        start = today - timedelta(days=days - 1)
        previous_end = start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=days - 1)
        return start, today, previous_start, previous_end

    def _empty_summary() -> dict[str, int]:
        return {
            **{field: 0 for field in SUMMARY_FIELDS},
            "xp_earned": 0,
            "active_members": 0,
        }

    def _member_totals(member: GroupMember) -> dict[str, Any]:
        return {
            "telegram_user_id": int(member.telegram_user_id),
            "display_name": member.display_name,
            "username": member.username,
            **{field: int(getattr(member, field)) for field in SUMMARY_FIELDS},
            "xp_total": int(member.xp_total),
            "xp_earned": int(member.xp_total),
            "current_streak": int(member.current_streak),
        }

    def _serialize_group(group: ChatGroup) -> dict[str, Any]:
        return {
            "telegram_chat_id": int(group.telegram_chat_id),
            "title": group.title,
            "username": group.username,
            "initials": MiniAppRepository._initials(group.title),
            "timezone": group.timezone,
        }

    def _serialize_settings(group: ChatGroup) -> dict[str, Any]:
        return {
            "is_paused": bool(group.is_paused),
            "weekly_reports_enabled": bool(group.weekly_reports_enabled),
            "timezone": group.timezone,
            "report_weekday": int(group.report_weekday),
            "report_time": f"{int(group.report_hour):02d}:{int(group.report_minute):02d}",
            "report_card_theme": group.report_card_theme,
            "track_messages": bool(group.track_messages),
            "track_media": bool(group.track_media),
            "track_replies": bool(group.track_replies),
            "track_reactions": bool(group.track_reactions),
        }

    def _nominations(members: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for field, title in METRICS:
            candidates = [item for item in members if int(item.get(field, 0)) > 0]
            if not candidates:
                continue
            winner = max(
                candidates,
                key=lambda item: (
                    int(item.get(field, 0)),
                    str(item["display_name"]).casefold(),
                ),
            )
            result.append(
                {
                    "metric": field,
                    "title": title,
                    "display_name": winner["display_name"],
                    "value": int(winner[field]),
                }
            )
        return result

    def _row_rank(rows: Sequence[dict[str, Any]], user_id: int) -> int | None:
        row = next(
            (item for item in rows if int(item["telegram_user_id"]) == user_id),
            None,
        )
        return int(row["rank"]) if row else None

    def _initials(value: str) -> str:
        pieces = [piece for piece in value.split() if piece]
        return "".join(piece[0].upper() for piece in pieces[:2]) or "CP"

    def _percentile(rank: int, total: int) -> int:
        if total <= 1:
            return 100
        return max(1, round((1 - ((rank - 1) / total)) * 100))

    def _achievement_category(field: str) -> str:
        if field == "current_streak":
            return "streak"
        if field == "reactions_received":
            return "reactions"
        if field in {"photo_count", "voice_count"}:
            return "media"
        if field == "level":
            return "levels"
        return "activity"
