from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, utc_now


class EngagementProfile(Base):
    __tablename__ = "engagement_profiles"

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    private_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_retention_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_retention_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OnboardingGroupLink(Base):
    __tablename__ = "onboarding_group_links"
    __table_args__ = (Index("ix_onboarding_group_links_chat", "telegram_chat_id"),)

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_groups.telegram_chat_id", ondelete="CASCADE"),
        primary_key=True,
    )
    bot_status: Mapped[str] = mapped_column(String(32), default="member")
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EngagementNotification(Base):
    __tablename__ = "engagement_notifications"
    __table_args__ = (
        UniqueConstraint(
            "telegram_user_id",
            "notification_key",
            name="uq_engagement_notification_user_key",
        ),
        Index("ix_engagement_notifications_sent", "sent_at"),
        Index("ix_engagement_notifications_type", "notification_type", "claimed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    notification_type: Mapped[str] = mapped_column(String(48), nullable=False)
    notification_key: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="claimed", nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EngagementRankSnapshot(Base):
    __tablename__ = "engagement_rank_snapshots"

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_groups.telegram_chat_id", ondelete="CASCADE"),
        primary_key=True,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
