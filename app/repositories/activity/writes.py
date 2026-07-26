from collections import Counter
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import MessageActivity, StatsPeriod, UserData
from app.models import (
    ChatGroup,
    DailyReactionEmoji,
    GroupMember,
    MessageAuthor,
    MessageReactionState,
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


class ActivityWritesMixin:
    async def record_message(
        self,
        *,
        chat_id: int,
        user: UserData,
        activity: MessageActivity,
        occurred_at: datetime,
        message_id: int | None = None,
    ) -> bool:
        async with self._session_factory() as session, session.begin():
            return await self.record_message_in_session(
                session,
                chat_id=chat_id,
                user=user,
                activity=activity,
                occurred_at=occurred_at,
                message_id=message_id,
            )

    async def record_message_in_session(
        self,
        session: AsyncSession,
        *,
        chat_id: int,
        user: UserData,
        activity: MessageActivity,
        occurred_at: datetime,
        message_id: int | None = None,
    ) -> bool:
        timestamp = occurred_at.astimezone(UTC)
        group = await session.get(ChatGroup, chat_id)
        if group is None or not group.is_active or group.is_paused:
            return False

        tracked_message = group.track_messages
        tracked_media = activity.is_media and group.track_media
        tracked_reply = activity.is_reply and group.track_replies
        if not any((tracked_message, tracked_media, tracked_reply)):
            return False

        timezone = ZoneInfo(group.timezone)
        local_time = timestamp.astimezone(timezone)
        local_date = local_time.date()
        is_night = tracked_message and 0 <= local_time.hour < 6
        is_morning = tracked_message and 6 <= local_time.hour < 10

        await self._upsert_user(session, user, timestamp)
        member = await self._get_or_create_member(session, chat_id, user, timestamp)

        member.messages_count += int(tracked_message)
        member.media_count += int(tracked_media)
        member.replies_count += int(tracked_reply)
        member.photo_count += int(activity.is_photo and group.track_media)
        member.voice_count += int(activity.is_voice and group.track_media)
        member.night_messages_count += int(is_night)
        member.morning_messages_count += int(is_morning)
        member.last_seen_at = timestamp

        daily = await self._get_or_create_daily(session, chat_id, user.telegram_id, local_date)
        daily.messages_count += int(tracked_message)
        daily.media_count += int(tracked_media)
        daily.replies_count += int(tracked_reply)
        daily.photo_count += int(activity.is_photo and group.track_media)
        daily.voice_count += int(activity.is_voice and group.track_media)
        daily.night_messages_count += int(is_night)
        daily.morning_messages_count += int(is_morning)

        if message_id is not None:
            author = await session.get(MessageAuthor, (chat_id, message_id))
            if author is None:
                session.add(
                    MessageAuthor(
                        telegram_chat_id=chat_id,
                        message_id=message_id,
                        telegram_user_id=user.telegram_id,
                        created_at=timestamp,
                    )
                )
                await session.flush()
        return True

    async def record_reaction(
        self,
        *,
        chat_id: int,
        message_id: int,
        old_reactions: Sequence[str],
        new_reactions: Sequence[str],
        occurred_at: datetime,
    ) -> bool:
        async with self._session_factory() as session, session.begin():
            return await self.record_reaction_in_session(
                session,
                chat_id=chat_id,
                message_id=message_id,
                old_reactions=old_reactions,
                new_reactions=new_reactions,
                occurred_at=occurred_at,
            )

    async def record_reaction_in_session(
        self,
        session: AsyncSession,
        *,
        chat_id: int,
        message_id: int,
        old_reactions: Sequence[str],
        new_reactions: Sequence[str],
        occurred_at: datetime,
    ) -> bool:
        timestamp = occurred_at.astimezone(UTC)
        group = await session.get(ChatGroup, chat_id)
        if group is None or not group.is_active or group.is_paused or not group.track_reactions:
            return False

        author = await session.get(MessageAuthor, (chat_id, message_id))
        if author is None:
            return False

        member = await session.get(GroupMember, (chat_id, author.telegram_user_id))
        if member is None:
            return False

        local_date = timestamp.astimezone(ZoneInfo(group.timezone)).date()
        daily = await self._get_or_create_daily(
            session, chat_id, author.telegram_user_id, local_date
        )

        old_counter = Counter(old_reactions)
        new_counter = Counter(new_reactions)
        total_delta = sum(new_counter.values()) - sum(old_counter.values())
        member.reactions_received = max(0, member.reactions_received + total_delta)
        daily.reactions_received = max(0, daily.reactions_received + total_delta)

        for emoji_key in set(old_counter) | set(new_counter):
            delta = new_counter[emoji_key] - old_counter[emoji_key]
            if delta == 0:
                continue
            reaction = await session.get(DailyReactionEmoji, (chat_id, local_date, emoji_key))
            if reaction is None:
                if delta > 0:
                    session.add(
                        DailyReactionEmoji(
                            telegram_chat_id=chat_id,
                            activity_date=local_date,
                            emoji_key=emoji_key,
                            reactions_count=delta,
                        )
                    )
                continue
            reaction.reactions_count = max(0, reaction.reactions_count + delta)
        return True

    async def record_reaction_count(
        self,
        *,
        chat_id: int,
        message_id: int,
        reaction_counts: dict[str, int],
        occurred_at: datetime,
    ) -> bool:
        async with self._session_factory() as session, session.begin():
            return await self.record_reaction_count_in_session(
                session,
                chat_id=chat_id,
                message_id=message_id,
                reaction_counts=reaction_counts,
                occurred_at=occurred_at,
            )

    async def record_reaction_count_in_session(
        self,
        session: AsyncSession,
        *,
        chat_id: int,
        message_id: int,
        reaction_counts: dict[str, int],
        occurred_at: datetime,
    ) -> bool:
        timestamp = occurred_at.astimezone(UTC)
        group = await session.get(ChatGroup, chat_id)
        if group is None or not group.is_active or group.is_paused or not group.track_reactions:
            return False
        author = await session.get(MessageAuthor, (chat_id, message_id))
        if author is None:
            return False
        member = await session.get(GroupMember, (chat_id, author.telegram_user_id))
        if member is None:
            return False

        result = await session.scalars(
            select(MessageReactionState).where(
                MessageReactionState.telegram_chat_id == chat_id,
                MessageReactionState.message_id == message_id,
            )
        )
        states = {row.emoji_key: row for row in result.all()}
        old_counts = {key: row.reactions_count for key, row in states.items()}
        local_date = timestamp.astimezone(ZoneInfo(group.timezone)).date()
        daily = await self._get_or_create_daily(
            session, chat_id, author.telegram_user_id, local_date
        )
        total_delta = sum(reaction_counts.values()) - sum(old_counts.values())
        member.reactions_received = max(0, member.reactions_received + total_delta)
        daily.reactions_received = max(0, daily.reactions_received + total_delta)

        for emoji_key in set(old_counts) | set(reaction_counts):
            old_value = old_counts.get(emoji_key, 0)
            new_value = reaction_counts.get(emoji_key, 0)
            delta = new_value - old_value
            state = states.get(emoji_key)
            if state is None and new_value > 0:
                session.add(
                    MessageReactionState(
                        telegram_chat_id=chat_id,
                        message_id=message_id,
                        emoji_key=emoji_key,
                        reactions_count=new_value,
                    )
                )
            elif state is not None:
                if new_value == 0:
                    await session.delete(state)
                else:
                    state.reactions_count = new_value

            if delta == 0:
                continue
            reaction = await session.get(DailyReactionEmoji, (chat_id, local_date, emoji_key))
            if reaction is None:
                if delta > 0:
                    session.add(
                        DailyReactionEmoji(
                            telegram_chat_id=chat_id,
                            activity_date=local_date,
                            emoji_key=emoji_key,
                            reactions_count=delta,
                        )
                    )
            else:
                reaction.reactions_count = max(0, reaction.reactions_count + delta)
        return True
