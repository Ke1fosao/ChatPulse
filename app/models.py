from datetime import UTC, date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
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
    global_xp_total: Mapped[int] = mapped_column(Integer, default=0)
    global_level: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BotOwner(Base):
    __tablename__ = "bot_owner"
    __table_args__ = (CheckConstraint("owner_key = 'primary'", name="ck_bot_owner_singleton"),)

    owner_key: Mapped[str] = mapped_column(String(16), primary_key=True, default="primary")
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    claimed_username: Mapped[str] = mapped_column(String(64), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VipGrant(Base):
    __tablename__ = "vip_grants"
    __table_args__ = (
        CheckConstraint(
            "expires_at IS NULL OR expires_at > starts_at",
            name="ck_vip_grants_valid_expiry",
        ),
        Index("ix_vip_grants_active_expiry", "is_active", "expires_at"),
    )

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_by_owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    grant_reason: Mapped[str] = mapped_column(String(300), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_owner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OwnerAuditLog(Base):
    __tablename__ = "owner_audit_log"
    __table_args__ = (
        Index("ix_owner_audit_created", "created_at"),
        Index("ix_owner_audit_target", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


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
    report_card_theme: Mapped[str] = mapped_column(String(32), default="dark_pulse")
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
    xp_total: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_streak_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)


class GlobalDailyXP(Base):
    __tablename__ = "global_daily_xp"

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    activity_date: Mapped[date] = mapped_column(Date, primary_key=True)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)


class MessageAuthor(Base):
    __tablename__ = "message_authors"
    __table_args__ = (
        Index(
            "ix_message_authors_user_created",
            "telegram_chat_id",
            "telegram_user_id",
            "created_at",
        ),
        Index(
            "ix_message_authors_reactions",
            "telegram_chat_id",
            "reactions_count",
            "created_at",
        ),
    )

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
    content_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_simhash: Mapped[str | None] = mapped_column(String(16), nullable=True)
    content_length: Mapped[int] = mapped_column(Integer, default=0)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    reactions_count: Mapped[int] = mapped_column(Integer, default=0)
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


class StreakProtectionUsage(Base):
    __tablename__ = "streak_protection_usage"

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
    month_start: Mapped[date] = mapped_column(Date, primary_key=True)
    used_days: Mapped[int] = mapped_column(Integer, default=0)


class MemberAchievement(Base):
    __tablename__ = "member_achievements"
    __table_args__ = (Index("ix_member_achievements_earned", "telegram_chat_id", "earned_at"),)

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
    achievement_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProcessedUpdate(Base):
    __tablename__ = "processed_updates"

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    update_type: Mapped[str] = mapped_column(String(64), default="unknown")
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
