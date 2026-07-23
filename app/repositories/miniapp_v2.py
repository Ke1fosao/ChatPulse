from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.achievement_models import AchievementUnlockRecord
from app.achievements.catalog import ACHIEVEMENTS
from app.achievements.presentation import achievement_progress_payload
from app.models import ChatGroup, DailyActivity, GroupMember, MemberAchievement, User, utc_now
from app.repositories.miniapp import MiniAppRepository
from app.services.miniapp import percentage_change

PremiumAnalyticsPeriod = Literal["quarter", "half_year", "year"]
PREMIUM_PERIOD_DAYS: dict[PremiumAnalyticsPeriod, int] = {
    "quarter": 90,
    "half_year": 180,
    "year": 365,
}


class AchievementMiniAppRepository(MiniAppRepository):
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

            user = await session.get(User, user_id)
            if user is None:
                return None

            progress_values: dict[str, int] = {
                "global_xp_total": int(user.global_xp_total),
                "global_level": int(user.global_level),
                "groups_count": len(memberships),
            }
            group_fields = (
                "messages_count",
                "media_count",
                "replies_count",
                "reactions_received",
                "photo_count",
                "voice_count",
                "night_messages_count",
                "morning_messages_count",
                "xp_total",
                "level",
                "current_streak",
            )
            for _group, member in memberships:
                for field in group_fields:
                    progress_values[field] = max(
                        progress_values.get(field, 0),
                        int(getattr(member, field, 0)),
                    )

            progress_values["active_days_total"] = int(
                await session.scalar(
                    select(func.count(func.distinct(DailyActivity.activity_date))).where(
                        DailyActivity.telegram_user_id == user_id,
                        DailyActivity.xp_earned > 0,
                    )
                )
                or 0
            )

            seven_days_ago = utc_now().astimezone(UTC).date() - timedelta(days=6)
            weekly_rows = await session.execute(
                select(
                    DailyActivity.telegram_chat_id,
                    func.sum(DailyActivity.xp_earned),
                )
                .where(
                    DailyActivity.telegram_user_id == user_id,
                    DailyActivity.activity_date >= seven_days_ago,
                )
                .group_by(DailyActivity.telegram_chat_id)
            )
            progress_values["xp_7d"] = max(
                (int(row[1] or 0) for row in weekly_rows.all()),
                default=0,
            )

            best_rank = 0
            for group, member in memberships:
                rank = (
                    int(
                        await session.scalar(
                            select(func.count())
                            .select_from(GroupMember)
                            .where(
                                GroupMember.telegram_chat_id == group.telegram_chat_id,
                                GroupMember.xp_total > member.xp_total,
                            )
                        )
                        or 0
                    )
                    + 1
                )
                best_rank = rank if best_rank == 0 else min(best_rank, rank)
            progress_values["rank"] = best_rank

            instances: dict[str, dict[str, dict[str, Any]]] = {}
            canonical_query = (
                select(AchievementUnlockRecord, ChatGroup.title)
                .outerjoin(
                    ChatGroup,
                    ChatGroup.telegram_chat_id == AchievementUnlockRecord.telegram_chat_id,
                )
                .where(AchievementUnlockRecord.telegram_user_id == user_id)
                .order_by(AchievementUnlockRecord.earned_at.desc())
            )
            if chat_id is not None:
                canonical_query = canonical_query.where(
                    AchievementUnlockRecord.telegram_chat_id == chat_id
                )
            for row in (await session.execute(canonical_query)).all():
                record = row.AchievementUnlockRecord
                code_instances = instances.setdefault(record.achievement_code, {})
                code_instances[record.scope_key] = {
                    "scope_key": record.scope_key,
                    "telegram_chat_id": (
                        int(record.telegram_chat_id)
                        if record.telegram_chat_id is not None
                        else None
                    ),
                    "group_title": str(row.title) if row.title is not None else None,
                    "earned_at": record.earned_at.isoformat(),
                    "progress": int(record.final_progress),
                }

            legacy_query = (
                select(MemberAchievement, ChatGroup.title)
                .join(
                    ChatGroup,
                    ChatGroup.telegram_chat_id == MemberAchievement.telegram_chat_id,
                )
                .where(MemberAchievement.telegram_user_id == user_id)
                .order_by(MemberAchievement.earned_at.desc())
            )
            if chat_id is not None:
                legacy_query = legacy_query.where(MemberAchievement.telegram_chat_id == chat_id)
            for row in (await session.execute(legacy_query)).all():
                record = row.MemberAchievement
                scope_key = f"group:{int(record.telegram_chat_id)}"
                code_instances = instances.setdefault(record.achievement_code, {})
                code_instances.setdefault(
                    scope_key,
                    {
                        "scope_key": scope_key,
                        "telegram_chat_id": int(record.telegram_chat_id),
                        "group_title": str(row.title),
                        "earned_at": record.earned_at.isoformat(),
                        "progress": 0,
                    },
                )

            result: list[dict[str, Any]] = []
            for definition in ACHIEVEMENTS:
                current_progress = int(progress_values.get(definition.metric, 0))
                earned_instances = sorted(
                    instances.get(definition.code, {}).values(),
                    key=lambda item: str(item["earned_at"]),
                    reverse=True,
                )
                is_earned = bool(earned_instances)
                highest_unlock_progress = max(
                    (int(item["progress"]) for item in earned_instances),
                    default=0,
                )
                final_progress = max(current_progress, highest_unlock_progress)
                primary = earned_instances[0] if earned_instances else None
                payload = definition.to_public_dict(
                    earned=is_earned,
                    progress=final_progress,
                    earned_at=str(primary["earned_at"]) if primary else None,
                    group_title=(
                        str(primary["group_title"])
                        if primary and primary["group_title"] is not None
                        else None
                    ),
                )
                payload.update(
                    achievement_progress_payload(
                        definition,
                        progress=final_progress,
                        earned=is_earned,
                    )
                )
                payload["earned_instances"] = earned_instances
                payload["primary_scope_key"] = str(primary["scope_key"]) if primary else None
                result.append(payload)
            return result
