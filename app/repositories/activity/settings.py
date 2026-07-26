from datetime import date, timedelta
from typing import Any

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.domain import GroupData, StatsPeriod, UserData
from app.models import (
    ChatGroup,
    DailyActivity,
    DailyReactionEmoji,
    GroupMember,
    MessageAuthor,
    MessageReactionState,
    ProcessedUpdate,
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


class ActivitySettingsMixin:
    async def claim_update(self, update_id: int, update_type: str) -> bool:
        async with self._session_factory() as session:
            session.add(ProcessedUpdate(update_id=update_id, update_type=update_type))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return False
            return True

    async def upsert_user(self, data: UserData) -> None:
        async with self._session_factory() as session, session.begin():
            await self._upsert_user(session, data, utc_now())

    async def upsert_group(
        self,
        data: GroupData,
        *,
        bot_status: str,
        is_active: bool,
    ) -> None:
        now = utc_now()
        async with self._session_factory() as session, session.begin():
            group = await session.get(ChatGroup, data.telegram_chat_id)
            if group is None:
                session.add(
                    ChatGroup(
                        telegram_chat_id=data.telegram_chat_id,
                        title=data.title,
                        username=data.username,
                        bot_status=bot_status,
                        is_active=is_active,
                        timezone=data.timezone,
                        created_at=now,
                        updated_at=now,
                    )
                )
                return

            group.title = data.title
            group.username = data.username
            group.bot_status = bot_status
            group.is_active = is_active
            if not group.timezone:
                group.timezone = data.timezone
            group.updated_at = now

    async def get_group_settings(self, chat_id: int) -> GroupSettings | None:
        async with self._session_factory() as session:
            group = await session.get(ChatGroup, chat_id)
            return self._serialize_group(group) if group else None

    async def update_group_setting(self, chat_id: int, field: str, value: Any) -> GroupSettings:
        allowed = {
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
        if field not in allowed:
            raise ValueError(f"Unsupported group setting: {field}")

        async with self._session_factory() as session, session.begin():
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                raise LookupError("Group is not registered")
            setattr(group, field, value)
            group.updated_at = utc_now()
            await session.flush()
            return self._serialize_group(group)

    async def reset_group_stats(self, chat_id: int) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                delete(DailyReactionEmoji).where(DailyReactionEmoji.telegram_chat_id == chat_id)
            )
            await session.execute(
                delete(MessageReactionState).where(MessageReactionState.telegram_chat_id == chat_id)
            )
            await session.execute(
                delete(MessageAuthor).where(MessageAuthor.telegram_chat_id == chat_id)
            )
            await session.execute(
                delete(DailyActivity).where(DailyActivity.telegram_chat_id == chat_id)
            )
            await session.execute(
                delete(GroupMember).where(GroupMember.telegram_chat_id == chat_id)
            )
