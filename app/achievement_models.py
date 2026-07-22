from datetime import datetime

from sqlalchemy import (
    BigInteger,
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


class AchievementUnlockRecord(Base):
    __tablename__ = "achievement_unlocks"
    __table_args__ = (
        CheckConstraint("scope IN ('group', 'global')", name="ck_achievement_unlock_scope"),
        UniqueConstraint(
            "telegram_user_id",
            "scope_key",
            "achievement_code",
            name="uq_achievement_unlock_identity",
        ),
        Index("ix_achievement_unlock_user_earned", "telegram_user_id", "earned_at"),
        Index("ix_achievement_unlock_group_earned", "telegram_chat_id", "earned_at"),
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
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(64), nullable=False)
    achievement_code: Mapped[str] = mapped_column(String(64), nullable=False)
    rarity: Mapped[str] = mapped_column(String(16), nullable=False)
    final_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    definition_version: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AchievementEventRecord(Base):
    __tablename__ = "achievement_events"
    __table_args__ = (
        Index("ix_achievement_events_pending", "telegram_user_id", "seen_at", "created_at"),
        Index("ix_achievement_events_unlock", "achievement_unlock_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    achievement_unlock_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("achievement_unlocks.id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), default="unlock", nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AchievementProgress(Base):
    __tablename__ = "achievement_progress"
    __table_args__ = (
        Index("ix_achievement_progress_user", "telegram_user_id", "updated_at"),
    )

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    scope_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    achievement_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("chat_groups.telegram_chat_id", ondelete="CASCADE"),
        nullable=True,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FeaturedAchievement(Base):
    __tablename__ = "featured_achievements"
    __table_args__ = (
        CheckConstraint("slot BETWEEN 1 AND 3", name="ck_featured_achievement_slot"),
        UniqueConstraint(
            "telegram_user_id",
            "scope_key",
            "achievement_code",
            name="uq_featured_achievement_identity",
        ),
    )

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    slot: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope_key: Mapped[str] = mapped_column(String(64), nullable=False)
    achievement_code: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
