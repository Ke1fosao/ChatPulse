from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
    ACHIEVEMENTS,
    ACHIEVEMENT_BY_CODE,
    MONTHLY_PROTECTION_DAYS,
    level_progress,
    level_tier,
)
from app.services.miniapp import message_link, percentage_change
from app.services.nominations import METRICS

MiniAppPeriod = Literal["week", "month", "all"]
RankingMetric = Literal["xp", "messages", "reactions", "replies", "streak"]

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


class MiniAppRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

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

            rank = int(
                await session.scalar(
                    select(func.count())
                    .select_from(User)
                    .where(User.global_xp_total > user.global_xp_total)
                )
                or 0
            ) + 1
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
                    "messages_7d": sum(
                        int(item["period"]["messages_count"]) for item in groups
                    ),
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

    async def get_achievements(
        self,
        user_id: int,
        chat_id: int | None = None,
    ) -> list[dict[str, Any]] | None:
        async with self._session_factory() as session:
            memberships = await self._memberships(session, user_id)
            if chat_id is not None:
                memberships = [
                    item for item in memberships if int(item[0].telegram_chat_id) == chat_id
                ]
                if not memberships:
                    return None

            progress_values: dict[str, int] = {}
            for _group, member in memberships:
                for definition in ACHIEVEMENTS:
                    progress_values[definition.field] = max(
                        progress_values.get(definition.field, 0),
                        int(getattr(member, definition.field, 0)),
                    )

            query = (
                select(MemberAchievement, ChatGroup.title)
                .join(
                    ChatGroup,
                    ChatGroup.telegram_chat_id == MemberAchievement.telegram_chat_id,
                )
                .where(MemberAchievement.telegram_user_id == user_id)
            )
            if chat_id is not None:
                query = query.where(MemberAchievement.telegram_chat_id == chat_id)
            rows = (await session.execute(query)).all()
            earned = {
                row.MemberAchievement.achievement_code: {
                    "earned_at": row.MemberAchievement.earned_at.isoformat(),
                    "group_title": row.title,
                }
                for row in rows
            }

            result: list[dict[str, Any]] = []
            for definition in ACHIEVEMENTS:
                current = progress_values.get(definition.field, 0)
                earned_data = earned.get(definition.code)
                result.append(
                    {
                        "code": definition.code,
                        "title": definition.title,
                        "description": definition.description,
                        "category": self._achievement_category(definition.field),
                        "rarity": "epic" if definition.important else "common",
                        "important": definition.important,
                        "earned": earned_data is not None,
                        "earned_at": earned_data["earned_at"] if earned_data else None,
                        "group_title": earned_data["group_title"] if earned_data else None,
                        "progress": min(current, definition.threshold),
                        "threshold": definition.threshold,
                    }
                )
            return result

    async def get_private_summary(self, user_id: int) -> dict[str, Any] | None:
        home = await self.get_home(user_id)
        if home is None:
            return None
        return {
            "display_name": home["user"]["display_name"],
            "global_progress": home["global_progress"],
            "quick_stats": home["quick_stats"],
            "groups": home["groups"],
            "recent_achievements": home["recent_achievements"],
        }

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
                func.coalesce(func.sum(getattr(GroupMember, field)), 0)
                for field in SUMMARY_FIELDS
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

    async def _protection_left(
        self,
        session: AsyncSession,
        group: ChatGroup,
        user_id: int,
        current: datetime,
    ) -> int:
        local_today = current.astimezone(ZoneInfo(group.timezone)).date()
        month_start = local_today.replace(day=1)
        usage = await session.get(
            StreakProtectionUsage,
            (int(group.telegram_chat_id), user_id, month_start),
        )
        used = int(usage.used_days) if usage else 0
        return max(0, MONTHLY_PROTECTION_DAYS - used)

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

    @staticmethod
    def _empty_summary() -> dict[str, int]:
        return {
            **{field: 0 for field in SUMMARY_FIELDS},
            "xp_earned": 0,
            "active_members": 0,
        }

    @staticmethod
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

    @staticmethod
    def _serialize_group(group: ChatGroup) -> dict[str, Any]:
        return {
            "telegram_chat_id": int(group.telegram_chat_id),
            "title": group.title,
            "username": group.username,
            "initials": MiniAppRepository._initials(group.title),
            "timezone": group.timezone,
        }

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def _row_rank(rows: Sequence[dict[str, Any]], user_id: int) -> int | None:
        row = next(
            (item for item in rows if int(item["telegram_user_id"]) == user_id),
            None,
        )
        return int(row["rank"]) if row else None

    @staticmethod
    def _initials(value: str) -> str:
        pieces = [piece for piece in value.split() if piece]
        return "".join(piece[0].upper() for piece in pieces[:2]) or "CP"

    @staticmethod
    def _percentile(rank: int, total: int) -> int:
        if total <= 1:
            return 100
        return max(1, round((1 - ((rank - 1) / total)) * 100))

    @staticmethod
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
