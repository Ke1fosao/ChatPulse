from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.engagement_models import EngagementRankSnapshot
from app.groups_v2_models import UserGroupPreference
from app.models import (
    ChatGroup,
    DailyActivity,
    GroupMember,
    MemberAchievement,
    OwnerAuditLog,
    utc_now,
)
from app.repositories.miniapp import MiniAppPeriod, MiniAppRepository, RankingMetric
from app.services.groups_v2 import (
    build_group_insights,
    calculate_group_pulse,
    derive_group_status,
)
from app.services.miniapp import percentage_change

_VALID_USERNAME = re.compile(r"^[A-Za-z0-9_]{5,32}$")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _period_days(period: MiniAppPeriod) -> int:
    return {"week": 7, "month": 30, "all": 30}[period]


def _empty_summary() -> dict[str, int]:
    return {
        "messages_count": 0,
        "media_count": 0,
        "replies_count": 0,
        "reactions_received": 0,
        "photo_count": 0,
        "voice_count": 0,
        "night_messages_count": 0,
        "morning_messages_count": 0,
        "xp_earned": 0,
        "active_members": 0,
    }


def _consecutive_active_days(series: list[dict[str, Any]]) -> int:
    active_dates = sorted(
        {
            date.fromisoformat(str(point["date"]))
            for point in series
            if int(point.get("messages", 0)) > 0
        }
    )
    if not active_dates:
        return 0
    count = 1
    cursor = active_dates[-1]
    for activity_date in reversed(active_dates[:-1]):
        if activity_date != cursor - timedelta(days=1):
            break
        count += 1
        cursor = activity_date
    return count


def _telegram_group_url(username: str | None) -> str | None:
    normalized = (username or "").lstrip("@").strip()
    if not _VALID_USERNAME.fullmatch(normalized):
        return None
    return f"https://t.me/{normalized}"


class GroupsV2Repository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        miniapp_repository: MiniAppRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._miniapp = miniapp_repository or MiniAppRepository(session_factory)

    async def list_groups(
        self,
        user_id: int,
        *,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        current = _as_utc(now or utc_now())
        active_cards = {
            int(item["telegram_chat_id"]): item
            for item in await self._miniapp.list_groups(user_id, now=current)
        }
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(ChatGroup, GroupMember)
                    .join(
                        GroupMember,
                        GroupMember.telegram_chat_id == ChatGroup.telegram_chat_id,
                    )
                    .where(GroupMember.telegram_user_id == user_id)
                )
            ).all()
            items: list[dict[str, Any]] = []
            for row in rows:
                group = row.ChatGroup
                member = row.GroupMember
                chat_id = int(group.telegram_chat_id)
                card = dict(
                    active_cards.get(
                        chat_id,
                        {
                            "telegram_chat_id": chat_id,
                            "title": group.title,
                            "username": group.username,
                            "initials": MiniAppRepository._initials(group.title),
                            "level": int(member.level),
                            "xp_total": int(member.xp_total),
                            "current_streak": int(member.current_streak),
                            "rank": None,
                            "period": _empty_summary(),
                            "trend": None,
                            "is_admin": False,
                            "last_activity_at": member.last_seen_at.isoformat(),
                        },
                    )
                )
                preference = await session.get(UserGroupPreference, (user_id, chat_id))
                group_last_activity = await session.scalar(
                    select(func.max(GroupMember.last_seen_at)).where(
                        GroupMember.telegram_chat_id == chat_id
                    )
                )
                local_today = current.astimezone(ZoneInfo(group.timezone)).date()
                messages_today = int(
                    await session.scalar(
                        select(func.coalesce(func.sum(DailyActivity.messages_count), 0)).where(
                            DailyActivity.telegram_chat_id == chat_id,
                            DailyActivity.activity_date == local_today,
                        )
                    )
                    or 0
                )
                messages_7d = int(
                    await session.scalar(
                        select(func.coalesce(func.sum(DailyActivity.messages_count), 0)).where(
                            DailyActivity.telegram_chat_id == chat_id,
                            DailyActivity.activity_date >= local_today - timedelta(days=6),
                            DailyActivity.activity_date <= local_today,
                        )
                    )
                    or 0
                )
                previous_messages = int(
                    await session.scalar(
                        select(func.coalesce(func.sum(DailyActivity.messages_count), 0)).where(
                            DailyActivity.telegram_chat_id == chat_id,
                            DailyActivity.activity_date >= local_today - timedelta(days=13),
                            DailyActivity.activity_date <= local_today - timedelta(days=7),
                        )
                    )
                    or 0
                )
                bot_operational = bool(
                    group.is_active and group.bot_status in {"administrator", "creator"}
                )
                status = derive_group_status(
                    bot_operational=bot_operational,
                    is_paused=bool(group.is_paused),
                    last_activity_at=group_last_activity,
                    now=current,
                )
                card.update(
                    {
                        "status": status,
                        "is_favorite": bool(preference and preference.is_favorite),
                        "bot_operational": bot_operational,
                        "messages_today": messages_today,
                        "messages_7d": messages_7d,
                        "trend": percentage_change(messages_7d, previous_messages),
                        "attention_reason": status["attention_reason"],
                        "last_activity_at": (
                            _as_utc(group_last_activity).isoformat()
                            if group_last_activity
                            else card.get("last_activity_at")
                        ),
                    }
                )
                items.append(card)
        items.sort(
            key=lambda item: (
                item["status"]["id"] != "needs_setup",
                not bool(item["is_favorite"]),
                item["status"]["id"] not in {"active"},
                -datetime.fromisoformat(str(item["last_activity_at"])).timestamp(),
                str(item["title"]).casefold(),
            )
        )
        return items

    async def set_favorite(
        self,
        user_id: int,
        chat_id: int,
        is_favorite: bool,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            membership = await session.get(GroupMember, (chat_id, user_id))
            if membership is None:
                raise LookupError("Group membership does not exist")
            preference = await session.get(UserGroupPreference, (user_id, chat_id))
            if preference is None:
                preference = UserGroupPreference(
                    telegram_user_id=user_id,
                    telegram_chat_id=chat_id,
                    is_favorite=is_favorite,
                    created_at=current,
                    updated_at=current,
                )
                session.add(preference)
            else:
                preference.is_favorite = is_favorite
                preference.updated_at = current
            await session.flush()
            return {
                "telegram_chat_id": chat_id,
                "is_favorite": bool(preference.is_favorite),
            }

    async def get_overview(
        self,
        user_id: int,
        chat_id: int,
        period: MiniAppPeriod,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        current = _as_utc(now or utc_now())
        dashboard = await self._miniapp.get_group_dashboard(
            user_id,
            chat_id,
            period,
            now=current,
        )
        if dashboard is None:
            return None
        async with self._session_factory() as session:
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                return None
            total_members = int(
                await session.scalar(
                    select(func.count()).select_from(GroupMember).where(
                        GroupMember.telegram_chat_id == chat_id
                    )
                )
                or 0
            )
            last_activity_at = await session.scalar(
                select(func.max(GroupMember.last_seen_at)).where(
                    GroupMember.telegram_chat_id == chat_id
                )
            )
            rank_snapshot = await session.get(EngagementRankSnapshot, (user_id, chat_id))
            current_rank = dashboard["personal_progress"].get("rank")
            rank_change = (
                int(rank_snapshot.rank) - int(current_rank)
                if rank_snapshot is not None and current_rank is not None
                else None
            )
            recent_achievement = await session.scalar(
                select(MemberAchievement)
                .where(
                    MemberAchievement.telegram_chat_id == chat_id,
                    MemberAchievement.telegram_user_id == user_id,
                )
                .order_by(MemberAchievement.earned_at.desc())
                .limit(1)
            )

        series = list(dashboard["activity_series"])
        consecutive_days = _consecutive_active_days(series)
        strongest = max(series, key=lambda point: int(point.get("messages", 0)), default=None)
        pulse = calculate_group_pulse(
            dashboard["overview"]["current"],
            dashboard["overview"]["previous"],
            total_members=total_members,
            consecutive_active_days=consecutive_days,
            period_days=_period_days(period),
        )
        status = derive_group_status(
            bot_operational=bool(
                group.is_active and group.bot_status in {"administrator", "creator"}
            ),
            is_paused=bool(group.is_paused),
            last_activity_at=last_activity_at,
            now=current,
        )
        leader_name = (
            str(dashboard["leaderboard"][0]["display_name"])
            if dashboard["leaderboard"]
            else None
        )
        insights = build_group_insights(
            rank_change=rank_change,
            achievement_title=(
                str(recent_achievement.achievement_code) if recent_achievement else None
            ),
            record_messages=int(strongest["messages"]) if strongest else None,
            record_date=date.fromisoformat(str(strongest["date"])) if strongest else None,
            consecutive_active_days=consecutive_days,
            leader_name=leader_name,
            report_ready=bool(group.last_weekly_report_at),
        )
        return {
            "group": {
                **dashboard["group"],
                "status": status,
                "telegram_url": _telegram_group_url(group.username),
            },
            "period": period,
            "pulse": pulse,
            "personal_progress": {
                **dashboard["personal_progress"],
                "rank_change": rank_change,
            },
            "top_participants": dashboard["leaderboard"][:3],
            "insights": insights,
            "top_message": dashboard["top_message"],
            "popular_reaction": dashboard["popular_reaction"],
            "settings": dashboard["settings"],
        }

    async def get_ranking(
        self,
        user_id: int,
        chat_id: int,
        metric: RankingMetric,
        period: MiniAppPeriod,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        payload = await self._miniapp.get_rankings(
            user_id,
            chat_id,
            metric,
            period,
            now=now,
        )
        if payload is None:
            return None
        user_ids = [int(row["telegram_user_id"]) for row in payload["rows"]]
        async with self._session_factory() as session:
            snapshots = (
                await session.scalars(
                    select(EngagementRankSnapshot).where(
                        EngagementRankSnapshot.telegram_chat_id == chat_id,
                        EngagementRankSnapshot.telegram_user_id.in_(user_ids or [-1]),
                    )
                )
            ).all()
        previous = {int(item.telegram_user_id): int(item.rank) for item in snapshots}
        for row in payload["rows"]:
            old_rank = previous.get(int(row["telegram_user_id"]))
            row["rank_change"] = old_rank - int(row["rank"]) if old_rank else None
        if payload.get("current_user"):
            current_row = payload["current_user"]
            old_rank = previous.get(int(current_row["telegram_user_id"]))
            current_row["rank_change"] = old_rank - int(current_row["rank"]) if old_rank else None
        return payload

    async def get_analytics(
        self,
        user_id: int,
        chat_id: int,
        period: MiniAppPeriod,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        dashboard = await self._miniapp.get_group_dashboard(
            user_id,
            chat_id,
            period,
            now=now,
        )
        if dashboard is None:
            return None
        return {
            "group": dashboard["group"],
            "period": period,
            "overview": dashboard["overview"],
            "activity_series": dashboard["activity_series"],
            "heatmap": dashboard["heatmap"],
            "popular_reaction": dashboard["popular_reaction"],
            "settings": dashboard["settings"],
        }

    async def get_awards(
        self,
        user_id: int,
        chat_id: int,
        period: MiniAppPeriod,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        dashboard = await self._miniapp.get_group_dashboard(
            user_id,
            chat_id,
            period,
            now=now,
        )
        if dashboard is None:
            return None
        achievements = await self._miniapp.get_achievements(user_id, chat_id)
        if achievements is None:
            return None
        nearest = sorted(
            (item for item in achievements if not item["earned"]),
            key=lambda item: int(item["threshold"]) - int(item["progress"]),
        )[:3]
        highlighted = next(
            (
                item
                for item in achievements
                if item["earned"] and bool(item.get("important"))
            ),
            None,
        )
        return {
            "group": dashboard["group"],
            "period": period,
            "nominations": dashboard["nominations"],
            "achievements": achievements,
            "nearest": nearest,
            "highlighted": highlighted,
        }

    async def set_paused(
        self,
        *,
        actor_user_id: int,
        chat_id: int,
        is_paused: bool,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                raise LookupError("Group is not registered")
            group.is_paused = is_paused
            group.updated_at = current
            session.add(
                OwnerAuditLog(
                    owner_telegram_user_id=actor_user_id,
                    action="group.analytics_paused" if is_paused else "group.analytics_resumed",
                    target_type="group",
                    target_id=str(chat_id),
                    metadata_json=json.dumps(
                        {"is_paused": is_paused},
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    created_at=current,
                )
            )
            await session.flush()
            return {"telegram_chat_id": chat_id, "is_paused": bool(group.is_paused)}

    async def record_admin_action(
        self,
        actor_user_id: int,
        chat_id: int,
        action: str,
        metadata: dict[str, Any] | None = None,
        *,
        now: datetime | None = None,
    ) -> None:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            session.add(
                OwnerAuditLog(
                    owner_telegram_user_id=actor_user_id,
                    action=action,
                    target_type="group",
                    target_id=str(chat_id),
                    metadata_json=json.dumps(
                        metadata or {},
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    created_at=current,
                )
            )
