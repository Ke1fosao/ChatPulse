from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, utc_now


class OwnerPaymentNote(Base):
    __tablename__ = "owner_payment_notes"
    __table_args__ = (UniqueConstraint("payment_id", name="uq_owner_payment_note_payment"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vip_payments.id", ondelete="CASCADE"),
        nullable=False,
    )
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
