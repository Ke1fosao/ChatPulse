from datetime import UTC, date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ChatGroup(Base):
    __tablename__ = "chat_groups"

    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bot_status: Mapped[str] = mapped_column(String(32), default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Kyiv")
    weekly_reports_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    report_weekday: Mapped[int] = mapped_column(Integer, default=6)
    report_hour: Mapped[int] = mapped_column(Integer, default=19)
    report_minute: Mapped[int] = mapped_column(Integer, default=0)
    track_messages: Mapped[bool] = mapped_column(Boolean, default=True)
    track_media: Mapped[bool] = mapped_column(Boolean, default=True)
    track_replies: Mapped[bool] = mapped_column(Boolean, default=True)
    track_reactions: Mapped[bool] = mapped_column(Boolean, default=True)
    last_weekly_report_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class GroupMember(Base):
    __tablename__ = "group_members"

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_groups.telegram_chat_id", ondelete="CASCADE"),
        primary_key=True,
    )
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    messages_count: Mapped[int] = mapped_column(Integer, default=0)
    media_count: Mapped[int] = mapped_column(Integer, default=0)
    replies_count: Mapped[int] = mapped_column(Integer, default=0)
    reactions_received: Mapped[int] = mapped_column(Integer, default=0)
    photo_count: Mapped[int] = mapped_column(Integer, default=0)
    voice_count: Mapped[int] = mapped_column(Integer, default=0)
    night_messages_count: Mapped[int] = mapped_column(Integer, default=0)
    morning_messages_count: Mapped[int] = mapped_column(Integer, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DailyActivity(Base):
    __tablename__ = "daily_activity"

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_groups.telegram_chat_id", ondelete="CASCADE"),
        primary_key=True,
    )
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    activity_date: Mapped[date] = mapped_column(Date, primary_key=True)
    messages_count: Mapped[int] = mapped_column(Integer, default=0)
    media_count: Mapped[int] = mapped_column(Integer, default=0)
    replies_count: Mapped[int] = mapped_column(Integer, default=0)
    reactions_received: Mapped[int] = mapped_column(Integer, default=0)
    photo_count: Mapped[int] = mapped_column(Integer, default=0)
    voice_count: Mapped[int] = mapped_column(Integer, default=0)
    night_messages_count: Mapped[int] = mapped_column(Integer, default=0)
    morning_messages_count: Mapped[int] = mapped_column(Integer, default=0)


class MessageAuthor(Base):
    __tablename__ = "message_authors"

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_groups.telegram_chat_id", ondelete="CASCADE"),
        primary_key=True,
    )
    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MessageReactionState(Base):
    __tablename__ = "message_reaction_state"

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_groups.telegram_chat_id", ondelete="CASCADE"),
        primary_key=True,
    )
    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    emoji_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    reactions_count: Mapped[int] = mapped_column(Integer, default=0)


class DailyReactionEmoji(Base):
    __tablename__ = "daily_reaction_emoji"

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_groups.telegram_chat_id", ondelete="CASCADE"),
        primary_key=True,
    )
    activity_date: Mapped[date] = mapped_column(Date, primary_key=True)
    emoji_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    reactions_count: Mapped[int] = mapped_column(Integer, default=0)


class ProcessedUpdate(Base):
    __tablename__ = "processed_updates"

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    update_type: Mapped[str] = mapped_column(String(64), default="unknown")
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
