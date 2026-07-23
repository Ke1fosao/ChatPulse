from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.engagement_models import (
    EngagementNotification,
    EngagementProfile,
    EngagementRankSnapshot,
    OnboardingGroupLink,
)
from app.models import ChatGroup, GroupMember, User, utc_now

ACTIVE_BOT_STATUSES = {"member", "administrator", "creator"}
RETENTION_COOLDOWN = timedelta(hours=20)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class EngagementRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def mark_private_started(
        self,
        user_id: int,
        *,
        now: datetime | None = None,
    ) -> None:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            if await session.get(User, user_id) is None:
                raise LookupError("User is not registered")
            profile = await session.get(EngagementProfile, user_id)
            if profile is None:
                profile = EngagementProfile(
                    telegram_user_id=user_id,
                    private_started_at=current,
                    created_at=current,
                    updated_at=current,
                )
                session.add(profile)
            else:
                profile.private_started_at = profile.private_started_at or current
                profile.updated_at = current

    async def link_group(
        self,
        user_id: int,
        chat_id: int,
        *,
        bot_status: str,
        now: datetime | None = None,
    ) -> None:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            if await session.get(User, user_id) is None:
                raise LookupError("User is not registered")
            if await session.get(ChatGroup, chat_id) is None:
                raise LookupError("Group is not registered")
            link = await session.get(OnboardingGroupLink, (user_id, chat_id))
            if link is None:
                session.add(
                    OnboardingGroupLink(
                        telegram_user_id=user_id,
                        telegram_chat_id=chat_id,
                        bot_status=bot_status,
                        connected_at=current,
                        updated_at=current,
                    )
                )
            else:
                link.bot_status = bot_status
                link.updated_at = current

    async def get_onboarding(
        self,
        user_id: int,
        *,
        bot_username: str | None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            user = await session.get(User, user_id)
            if user is None:
                raise LookupError("User is not registered")
            profile = await session.get(EngagementProfile, user_id)
            started = bool(profile and profile.private_started_at)

            link_rows = (
                await session.execute(
                    select(OnboardingGroupLink, ChatGroup)
                    .join(
                        ChatGroup,
                        ChatGroup.telegram_chat_id == OnboardingGroupLink.telegram_chat_id,
                    )
                    .where(
                        OnboardingGroupLink.telegram_user_id == user_id,
                        ChatGroup.is_active.is_(True),
                    )
                    .order_by(OnboardingGroupLink.updated_at.desc())
                )
            ).all()
            active_links = [
                row
                for row in link_rows
                if str(row.OnboardingGroupLink.bot_status) in ACTIVE_BOT_STATUSES
            ]

            membership_rows = (
                await session.execute(
                    select(ChatGroup, GroupMember)
                    .join(
                        GroupMember,
                        GroupMember.telegram_chat_id == ChatGroup.telegram_chat_id,
                    )
                    .where(
                        GroupMember.telegram_user_id == user_id,
                        ChatGroup.is_active.is_(True),
                    )
                    .order_by(GroupMember.last_seen_at.desc())
                )
            ).all()
            connected = bool(active_links or membership_rows)
            first_activity = any(
                int(row.GroupMember.messages_count) > 0 for row in membership_rows
            )
            completed_flags = (started, connected, first_activity)
            completed_steps = sum(completed_flags)
            is_complete = completed_steps == 3

            if is_complete:
                if profile is None:
                    profile = EngagementProfile(
                        telegram_user_id=user_id,
                        private_started_at=current,
                        onboarding_completed_at=current,
                        created_at=current,
                        updated_at=current,
                    )
                    session.add(profile)
                elif profile.onboarding_completed_at is None:
                    profile.onboarding_completed_at = current
                    profile.updated_at = current

            linked_group: dict[str, Any] | None = None
            if active_links:
                group = active_links[0].ChatGroup
                linked_group = {
                    "telegram_chat_id": int(group.telegram_chat_id),
                    "title": group.title,
                    "username": group.username,
                }
            elif membership_rows:
                group = membership_rows[0].ChatGroup
                linked_group = {
                    "telegram_chat_id": int(group.telegram_chat_id),
                    "title": group.title,
                    "username": group.username,
                }

            normalized_username = (bot_username or "").lstrip("@")
            add_group_url = (
                f"https://t.me/{normalized_username}?startgroup=true"
                if normalized_username
                else None
            )
            if is_complete:
                primary_action = "done"
            elif not connected:
                primary_action = "add_group"
            else:
                primary_action = "send_message"

            return {
                "completed_steps": completed_steps,
                "total_steps": 3,
                "is_complete": is_complete,
                "primary_action": primary_action,
                "add_group_url": add_group_url,
                "linked_group": linked_group,
                "steps": [
                    {
                        "id": "start",
                        "title": "Запусти ChatPulse",
                        "description": "Особистий профіль створено",
                        "completed": started,
                    },
                    {
                        "id": "group",
                        "title": "Додай у групу",
                        "description": "Підключи групу й надай боту права адміністратора",
                        "completed": connected,
                    },
                    {
                        "id": "activity",
                        "title": "Створи перший пульс",
                        "description": "Напиши повідомлення та отримай першу статистику",
                        "completed": first_activity,
                    },
                ],
            }

    async def claim_notification(
        self,
        user_id: int,
        *,
        notification_type: str,
        notification_key: str,
        chat_id: int | None = None,
        now: datetime | None = None,
    ) -> int | None:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            profile = await session.get(EngagementProfile, user_id)
            if profile is None or profile.private_started_at is None:
                return None
            if profile.last_retention_sent_at is not None:
                last_sent = _as_utc(profile.last_retention_sent_at)
                if current - last_sent < RETENTION_COOLDOWN:
                    return None
            existing = await session.scalar(
                select(EngagementNotification.id).where(
                    EngagementNotification.telegram_user_id == user_id,
                    EngagementNotification.notification_key == notification_key[:180],
                )
            )
            if existing is not None:
                return None
            notification = EngagementNotification(
                telegram_user_id=user_id,
                telegram_chat_id=chat_id,
                notification_type=notification_type[:48],
                notification_key=notification_key[:180],
                status="claimed",
                claimed_at=current,
            )
            try:
                async with session.begin_nested():
                    session.add(notification)
                    await session.flush()
            except IntegrityError:
                return None
            return int(notification.id)

    async def mark_notification_sent(
        self,
        notification_id: int,
        *,
        now: datetime | None = None,
    ) -> None:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            notification = await session.get(EngagementNotification, notification_id)
            if notification is None:
                raise LookupError("Notification not found")
            notification.status = "sent"
            notification.sent_at = current
            profile = await session.get(EngagementProfile, notification.telegram_user_id)
            if profile is not None:
                profile.last_retention_sent_at = current
                profile.last_retention_type = notification.notification_type
                profile.updated_at = current

    async def release_notification(self, notification_id: int) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                delete(EngagementNotification).where(
                    EngagementNotification.id == notification_id,
                    EngagementNotification.status == "claimed",
                )
            )

    async def list_started_user_ids(self) -> list[int]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(EngagementProfile.telegram_user_id).where(
                    EngagementProfile.private_started_at.is_not(None)
                )
            )
            return [int(value) for value in rows.all()]

    async def get_streak_risk_candidate(
        self,
        user_id: int,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(ChatGroup, GroupMember)
                    .join(
                        GroupMember,
                        GroupMember.telegram_chat_id == ChatGroup.telegram_chat_id,
                    )
                    .where(
                        GroupMember.telegram_user_id == user_id,
                        GroupMember.current_streak > 0,
                        ChatGroup.is_active.is_(True),
                        ChatGroup.is_paused.is_(False),
                    )
                )
            ).all()
            candidates: list[dict[str, Any]] = []
            for row in rows:
                group = row.ChatGroup
                member = row.GroupMember
                local_now = current.astimezone(ZoneInfo(group.timezone))
                if not 19 <= local_now.hour < 23:
                    continue
                if member.last_streak_date == local_now.date():
                    continue
                candidates.append(
                    {
                        "telegram_chat_id": int(group.telegram_chat_id),
                        "group_title": group.title,
                        "streak": int(member.current_streak),
                        "local_date": local_now.date().isoformat(),
                    }
                )
            if not candidates:
                return None
            return max(candidates, key=lambda item: int(item["streak"]))

    async def list_weekly_user_ids(
        self,
        chat_id: int,
        *,
        since: datetime,
    ) -> list[int]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(GroupMember.telegram_user_id)
                .join(
                    EngagementProfile,
                    EngagementProfile.telegram_user_id == GroupMember.telegram_user_id,
                )
                .where(
                    GroupMember.telegram_chat_id == chat_id,
                    GroupMember.messages_count > 0,
                    GroupMember.last_seen_at >= since,
                    EngagementProfile.private_started_at.is_not(None),
                )
            )
            return [int(value) for value in rows.all()]

    async def get_group_xp_ranks(self, chat_id: int) -> dict[int, int]:
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(GroupMember.telegram_user_id, GroupMember.xp_total)
                    .where(GroupMember.telegram_chat_id == chat_id)
                    .order_by(
                        GroupMember.xp_total.desc(),
                        GroupMember.telegram_user_id.asc(),
                    )
                )
            ).all()
            return {int(row.telegram_user_id): index for index, row in enumerate(rows, start=1)}

    async def update_rank_snapshot(
        self,
        user_id: int,
        chat_id: int,
        *,
        rank: int,
        period_start: date,
        now: datetime | None = None,
    ) -> dict[str, int | None]:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            snapshot = await session.get(EngagementRankSnapshot, (user_id, chat_id))
            if snapshot is None:
                session.add(
                    EngagementRankSnapshot(
                        telegram_user_id=user_id,
                        telegram_chat_id=chat_id,
                        rank=rank,
                        period_start=period_start,
                        updated_at=current,
                    )
                )
                return {
                    "previous_rank": None,
                    "current_rank": rank,
                    "improved_by": 0,
                }

            previous_rank = int(snapshot.rank)
            same_period = snapshot.period_start == period_start
            improved_by = 0 if same_period else max(previous_rank - rank, 0)
            snapshot.rank = rank
            snapshot.period_start = period_start
            snapshot.updated_at = current
            return {
                "previous_rank": previous_rank,
                "current_rank": rank,
                "improved_by": improved_by,
            }
