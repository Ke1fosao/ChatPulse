from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, utc_now


class UserGroupPreference(Base):
    __tablename__ = "user_group_preferences"
    __table_args__ = (
        Index("ix_user_group_preferences_chat", "telegram_chat_id"),
        Index("ix_user_group_preferences_favorite", "telegram_user_id", "is_favorite"),
    )

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
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
