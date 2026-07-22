from __future__ import annotations

from datetime import UTC, timedelta
from typing import Any

from sqlalchemy import func, select

from app.achievement_models import AchievementUnlockRecord
from app.achievements.catalog import ACHIEVEMENTS
from app.achievements.presentation import achievement_progress_payload
from app.models import ChatGroup, DailyActivity, GroupMember, MemberAchievement, User, utc_now
from app.repositories.miniapp import MiniAppRepository


class AchievementMiniAppRepository(MiniAppRepository):
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

            canonical_query = (
                select(AchievementUnlockRecord, ChatGroup.title)
                .outerjoin(
                    ChatGroup,
                    ChatGroup.telegram_chat_id == AchievementUnlockRecord.telegram_chat_id,
                )
                .where(AchievementUnlockRecord.telegram_user_id == user_id)
            )
            if chat_id is not None:
                canonical_query = canonical_query.where(
                    AchievementUnlockRecord.telegram_chat_id == chat_id
                )
            canonical_rows = (await session.execute(canonical_query)).all()
            earned: dict[str, dict[str, Any]] = {
                row.AchievementUnlockRecord.achievement_code: {
                    "earned_at": row.AchievementUnlockRecord.earned_at.isoformat(),
                    "group_title": str(row.title) if row.title is not None else None,
                    "progress": int(row.AchievementUnlockRecord.final_progress),
                }
                for row in canonical_rows
            }

            legacy_query = (
                select(MemberAchievement, ChatGroup.title)
                .join(
                    ChatGroup,
                    ChatGroup.telegram_chat_id == MemberAchievement.telegram_chat_id,
                )
                .where(MemberAchievement.telegram_user_id == user_id)
            )
            if chat_id is not None:
                legacy_query = legacy_query.where(MemberAchievement.telegram_chat_id == chat_id)
            for row in (await session.execute(legacy_query)).all():
                earned.setdefault(
                    row.MemberAchievement.achievement_code,
                    {
                        "earned_at": row.MemberAchievement.earned_at.isoformat(),
                        "group_title": str(row.title),
                        "progress": 0,
                    },
                )

            result: list[dict[str, Any]] = []
            for definition in ACHIEVEMENTS:
                current = int(progress_values.get(definition.metric, 0))
                earned_data = earned.get(definition.code)
                final_progress = (
                    max(current, int(earned_data.get("progress", 0))) if earned_data else current
                )
                is_earned = earned_data is not None
                payload = definition.to_public_dict(
                    earned=is_earned,
                    progress=final_progress,
                    earned_at=earned_data["earned_at"] if earned_data else None,
                    group_title=earned_data["group_title"] if earned_data else None,
                )
                payload.update(
                    achievement_progress_payload(
                        definition,
                        progress=final_progress,
                        earned=is_earned,
                    )
                )
                result.append(payload)
            return result
