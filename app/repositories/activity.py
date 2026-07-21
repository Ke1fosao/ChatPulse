from collections import Counter
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain import GroupData, MessageActivity, StatsPeriod, UserData
from app.models import (
    ChatGroup,
    DailyActivity,
    DailyReactionEmoji,
    GroupMember,
    MessageAuthor,
    MessageReactionState,
    ProcessedUpdate,
    User,
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


class ActivityRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

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

    async def record_message(
        self,
        *,
        chat_id: int,
        user: UserData,
        activity: MessageActivity,
        occurred_at: datetime,
        message_id: int | None = None,
    ) -> bool:
        timestamp = occurred_at.astimezone(UTC)
        async with self._session_factory() as session, session.begin():
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
        timestamp = occurred_at.astimezone(UTC)
        async with self._session_factory() as session, session.begin():
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
        timestamp = occurred_at.astimezone(UTC)
        async with self._session_factory() as session, session.begin():
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

    async def _get_or_create_member(
        self,
        session: AsyncSession,
        chat_id: int,
        user: UserData,
        timestamp: datetime,
    ) -> GroupMember:
        member = await session.get(GroupMember, (chat_id, user.telegram_id))
        if member is None:
            member = GroupMember(
                telegram_chat_id=chat_id,
                telegram_user_id=user.telegram_id,
                display_name=user.display_name,
                username=user.username,
                messages_count=0,
                media_count=0,
                replies_count=0,
                reactions_received=0,
                photo_count=0,
                voice_count=0,
                night_messages_count=0,
                morning_messages_count=0,
                first_seen_at=timestamp,
                last_seen_at=timestamp,
            )
            session.add(member)
        member.display_name = user.display_name
        member.username = user.username
        return member

    async def _get_or_create_daily(
        self,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        activity_date: date,
    ) -> DailyActivity:
        daily = await session.get(DailyActivity, (chat_id, user_id, activity_date))
        if daily is None:
            daily = DailyActivity(
                telegram_chat_id=chat_id,
                telegram_user_id=user_id,
                activity_date=activity_date,
                messages_count=0,
                media_count=0,
                replies_count=0,
                reactions_received=0,
                photo_count=0,
                voice_count=0,
                night_messages_count=0,
                morning_messages_count=0,
            )
            session.add(daily)
        return daily

    async def _upsert_user(
        self,
        session: AsyncSession,
        data: UserData,
        timestamp: datetime,
    ) -> User:
        user = await session.get(User, data.telegram_id)
        if user is None:
            user = User(
                telegram_id=data.telegram_id,
                username=data.username,
                first_name=data.first_name,
                last_name=data.last_name,
                language_code=data.language_code,
                created_at=timestamp,
                updated_at=timestamp,
                last_activity_at=timestamp,
            )
            session.add(user)
            return user

        user.username = data.username
        user.first_name = data.first_name
        user.last_name = data.last_name
        user.language_code = data.language_code
        user.updated_at = timestamp
        user.last_activity_at = timestamp
        return user

    @staticmethod
    def _serialize_member(member: GroupMember) -> MemberStats:
        return {
            "telegram_user_id": member.telegram_user_id,
            "display_name": member.display_name,
            "username": member.username,
            **{field: int(getattr(member, field)) for field in COUNTER_FIELDS},
        }

    @staticmethod
    def _serialize_group(group: ChatGroup) -> GroupSettings:
        return {
            "telegram_chat_id": group.telegram_chat_id,
            "title": group.title,
            "username": group.username,
            "timezone": group.timezone,
            "is_active": group.is_active,
            "is_paused": group.is_paused,
            "weekly_reports_enabled": group.weekly_reports_enabled,
            "report_weekday": group.report_weekday,
            "report_hour": group.report_hour,
            "report_minute": group.report_minute,
            "track_messages": group.track_messages,
            "track_media": group.track_media,
            "track_replies": group.track_replies,
            "track_reactions": group.track_reactions,
            "last_weekly_report_at": group.last_weekly_report_at,
        }
