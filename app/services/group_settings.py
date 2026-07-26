from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    ChatGroup,
    DailyActivity,
    DailyReactionEmoji,
    GroupMember,
    MemberAchievement,
    MessageAuthor,
    MessageReactionState,
    StreakProtectionUsage,
    utc_now,
)
from app.services.premium_policy import ALL_REPORT_THEMES, PREMIUM_REPORT_THEMES

logger = logging.getLogger("chatpulse.transactions")

Checkpoint = Callable[[str, AsyncSession], Awaitable[None] | None]

_ALLOWED_FIELDS = {
    "is_paused",
    "weekly_reports_enabled",
    "timezone",
    "report_weekday",
    "report_hour",
    "track_messages",
    "track_media",
    "track_replies",
    "track_reactions",
}


class GroupSettingsService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        checkpoint: Checkpoint | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._checkpoint_callback = checkpoint

    async def update_settings(
        self,
        *,
        actor_user_id: int,
        chat_id: int,
        values: Mapping[str, Any],
        premium_allowed: bool = False,
    ) -> dict[str, Any]:
        del actor_user_id  # Reserved for the audit boundary.
        try:
            async with self._session_factory() as session, session.begin():
                group = await session.get(ChatGroup, chat_id)
                if group is None:
                    raise LookupError("Group is not registered")

                mutable = dict(values)
                report_time = mutable.pop("report_time", None)
                report_theme = mutable.pop("report_card_theme", None)

                if report_time is not None:
                    hour, minute = (int(piece) for piece in str(report_time).split(":"))
                    group.report_hour = hour
                    group.report_minute = minute

                if report_theme is not None:
                    theme = str(report_theme)
                    if theme not in ALL_REPORT_THEMES:
                        raise ValueError("Unsupported report theme")
                    if theme in PREMIUM_REPORT_THEMES and not premium_allowed:
                        raise PermissionError("Ця тема доступна у ChatPulse VIP.")
                    group.report_card_theme = theme

                await self._checkpoint("extras_updated", session)

                unsupported = set(mutable) - _ALLOWED_FIELDS
                if unsupported:
                    raise ValueError(f"Unsupported group setting: {sorted(unsupported)[0]}")
                for field, value in mutable.items():
                    setattr(group, field, value)
                group.updated_at = utc_now()
                await session.flush()
                await self._checkpoint("settings_updated", session)
                return self._serialize(group)
        except Exception:
            logger.exception("transaction_rolled_back operation=group_settings chat_id=%s", chat_id)
            raise

    async def reset_group(self, *, actor_user_id: int, chat_id: int) -> None:
        del actor_user_id
        try:
            async with self._session_factory() as session, session.begin():
                group = await session.get(ChatGroup, chat_id)
                if group is None:
                    raise LookupError("Group is not registered")

                await session.execute(
                    delete(DailyReactionEmoji).where(DailyReactionEmoji.telegram_chat_id == chat_id)
                )
                await session.execute(
                    delete(MessageReactionState).where(
                        MessageReactionState.telegram_chat_id == chat_id
                    )
                )
                await session.execute(
                    delete(MessageAuthor).where(MessageAuthor.telegram_chat_id == chat_id)
                )
                await session.execute(
                    delete(DailyActivity).where(DailyActivity.telegram_chat_id == chat_id)
                )
                await self._checkpoint("activity_deleted", session)
                await session.execute(
                    delete(MemberAchievement).where(MemberAchievement.telegram_chat_id == chat_id)
                )
                await session.execute(
                    delete(StreakProtectionUsage).where(
                        StreakProtectionUsage.telegram_chat_id == chat_id
                    )
                )
                await session.execute(
                    delete(GroupMember).where(GroupMember.telegram_chat_id == chat_id)
                )
                await self._checkpoint("gamification_deleted", session)
        except Exception:
            logger.exception("transaction_rolled_back operation=group_reset chat_id=%s", chat_id)
            raise

    async def _checkpoint(self, name: str, session: AsyncSession) -> None:
        if self._checkpoint_callback is None:
            return
        result = self._checkpoint_callback(name, session)
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def _serialize(group: ChatGroup) -> dict[str, Any]:
        return {
            "telegram_chat_id": int(group.telegram_chat_id),
            "title": group.title,
            "username": group.username,
            "bot_status": group.bot_status,
            "is_active": bool(group.is_active),
            "is_paused": bool(group.is_paused),
            "weekly_reports_enabled": bool(group.weekly_reports_enabled),
            "timezone": group.timezone,
            "report_weekday": int(group.report_weekday),
            "report_hour": int(group.report_hour),
            "report_minute": int(group.report_minute),
            "report_time": f"{int(group.report_hour):02d}:{int(group.report_minute):02d}",
            "report_card_theme": group.report_card_theme,
            "track_messages": bool(group.track_messages),
            "track_media": bool(group.track_media),
            "track_replies": bool(group.track_replies),
            "track_reactions": bool(group.track_reactions),
        }
