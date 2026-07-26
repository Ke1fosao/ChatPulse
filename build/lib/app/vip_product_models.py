from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, utc_now


class VipProductEvent(Base):
    __tablename__ = "vip_product_events"
    __table_args__ = (
        Index("ix_vip_product_event_created", "created_at"),
        Index("ix_vip_product_event_user_created", "telegram_user_id", "created_at"),
        Index("ix_vip_product_event_type_source", "event_type", "source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_key: Mapped[str | None] = mapped_column(String(96), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
