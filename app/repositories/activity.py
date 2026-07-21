from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain import GroupData, MessageActivity, UserData
from app.models import ChatGroup, DailyActivity, GroupMember, User, utc_now

MemberStats = dict[str, Any]
GroupSummary = dict[str, int]


class ActivityRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

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
                group = ChatGroup(
                    telegram_chat_id=data.telegram_chat_id,
                    title=data.title,
                    username=data.username,
                    bot_status=bot_status,
                    is_active=is_active,
                    timezone=data.timezone,
                    created_at=now,
                    updated_at=now,
                )
                session.add(group)
                return

            group.title = data.title
            group.username = data.username
            group.bot_status = bot_status
            group.is_active = is_active
            group.timezone = data.timezone
            group.updated_at = now

    async def record_message(
        self,
        *,
        chat_id: int,
        user: UserData,
        activity: MessageActivity,
        occurred_at: datetime,
    ) -> bool:
        timestamp = occurred_at.astimezone(UTC)
        async with self._session_factory() as session, session.begin():
            group = await session.get(ChatGroup, chat_id)
            if group is None or not group.is_active:
                return False

            await self._upsert_user(session, user, timestamp)

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
                    first_seen_at=timestamp,
                    last_seen_at=timestamp,
                )
                session.add(member)

            member.display_name = user.display_name
            member.username = user.username
            member.messages_count += 1
            member.media_count += int(activity.is_media)
            member.replies_count += int(activity.is_reply)
            member.last_seen_at = timestamp

            daily = await session.get(
                DailyActivity,
                (chat_id, user.telegram_id, timestamp.date()),
            )
            if daily is None:
                daily = DailyActivity(
                    telegram_chat_id=chat_id,
                    telegram_user_id=user.telegram_id,
                    activity_date=timestamp.date(),
                    messages_count=0,
                    media_count=0,
                    replies_count=0,
                )
                session.add(daily)

            daily.messages_count += 1
            daily.media_count += int(activity.is_media)
            daily.replies_count += int(activity.is_reply)
            return True

    async def get_member_stats(self, chat_id: int, user_id: int) -> MemberStats | None:
        async with self._session_factory() as session:
            member = await session.get(GroupMember, (chat_id, user_id))
            return self._serialize_member(member) if member else None

    async def get_group_summary(self, chat_id: int) -> GroupSummary:
        async with self._session_factory() as session:
            result = await session.execute(
                select(
                    func.coalesce(func.sum(GroupMember.messages_count), 0),
                    func.coalesce(func.sum(GroupMember.media_count), 0),
                    func.coalesce(func.sum(GroupMember.replies_count), 0),
                    func.count(GroupMember.telegram_user_id),
                ).where(GroupMember.telegram_chat_id == chat_id)
            )
            messages, media, replies, members = result.one()
            return {
                "messages_count": int(messages),
                "media_count": int(media),
                "replies_count": int(replies),
                "active_members": int(members),
            }

    async def get_top_members(self, chat_id: int, *, limit: int = 10) -> list[MemberStats]:
        async with self._session_factory() as session:
            result = await session.scalars(
                select(GroupMember)
                .where(GroupMember.telegram_chat_id == chat_id)
                .order_by(
                    GroupMember.messages_count.desc(),
                    GroupMember.replies_count.desc(),
                    GroupMember.display_name.asc(),
                )
                .limit(limit)
            )
            members: Sequence[GroupMember] = result.all()
            return [self._serialize_member(member) for member in members]

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
            "messages_count": member.messages_count,
            "media_count": member.media_count,
            "replies_count": member.replies_count,
        }
