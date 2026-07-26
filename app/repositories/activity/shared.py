from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain import StatsPeriod, UserData
from app.models import (
    ChatGroup,
    DailyActivity,
    GroupMember,
    User,
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


class ActivityShared:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

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

    def _serialize_member(member: GroupMember) -> MemberStats:
        return {
            "telegram_user_id": member.telegram_user_id,
            "display_name": member.display_name,
            "username": member.username,
            **{field: int(getattr(member, field)) for field in COUNTER_FIELDS},
        }

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
