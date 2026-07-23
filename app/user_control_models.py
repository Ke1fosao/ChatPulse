from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, utc_now


class AdminStaff(Base):
    __tablename__ = "admin_staff"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'moderator', 'support')",
            name="ck_admin_staff_role",
        ),
        Index("ix_admin_staff_role_active", "role", "is_active"),
    )

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    granted_by_owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserRestriction(Base):
    __tablename__ = "user_restrictions"
    __table_args__ = (Index("ix_user_restrictions_blocked", "is_blocked", "updated_at"),)

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    blocked_by_actor_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unblocked_by_actor_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    unblocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unblock_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserAdminNote(Base):
    __tablename__ = "user_admin_notes"

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by_actor_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserAdminTag(Base):
    __tablename__ = "user_admin_tags"
    __table_args__ = (
        CheckConstraint("length(tag) BETWEEN 1 AND 32", name="ck_user_admin_tags_length"),
        Index("ix_user_admin_tags_tag", "tag"),
    )

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_by_actor_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserXpAdjustment(Base):
    __tablename__ = "user_xp_adjustments"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="ck_user_xp_adjustments_nonzero"),
        Index("ix_user_xp_adjustments_user_created", "telegram_user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    telegram_chat_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("chat_groups.telegram_chat_id", ondelete="CASCADE"),
        nullable=True,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_total: Mapped[int] = mapped_column(Integer, nullable=False)
    resulting_total: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    actor_telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AdminMessageDelivery(Base):
    __tablename__ = "admin_message_deliveries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name="ck_admin_message_deliveries_status",
        ),
        Index("ix_admin_message_deliveries_user_created", "telegram_user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    safe_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BlockedAccessEvent(Base):
    __tablename__ = "blocked_access_events"
    __table_args__ = (
        CheckConstraint(
            "source IN ('miniapp', 'bot_private', 'bot_group')",
            name="ck_blocked_access_events_source",
        ),
        UniqueConstraint(
            "telegram_user_id",
            "source",
            "window_key",
            name="uq_blocked_access_events_window",
        ),
        Index("ix_blocked_access_events_user_last", "telegram_user_id", "last_attempt_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    window_key: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
