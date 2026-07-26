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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, utc_now


class VipInvoiceIntent(Base):
    __tablename__ = "vip_invoice_intents"
    __table_args__ = (
        CheckConstraint("stars_amount > 0", name="ck_vip_invoice_positive_amount"),
        Index("ix_vip_invoice_user_created", "telegram_user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payload: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    product_code: Mapped[str] = mapped_column(String(32), nullable=False)
    stars_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VipPayment(Base):
    __tablename__ = "vip_payments"
    __table_args__ = (
        CheckConstraint("stars_amount > 0", name="ck_vip_payment_positive_amount"),
        UniqueConstraint(
            "telegram_payment_charge_id",
            name="uq_vip_payment_telegram_charge",
        ),
        Index("ix_vip_payment_user_paid", "telegram_user_id", "paid_at"),
        Index("ix_vip_payment_invoice", "invoice_intent_id", "paid_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_intent_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vip_invoice_intents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    product_code: Mapped[str] = mapped_column(String(32), nullable=False)
    stars_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_payment_charge_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_payment_charge_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_first_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription_expiration_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    granted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="paid", nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refund_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class VipTrialClaim(Base):
    __tablename__ = "vip_trial_claims"

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    payment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vip_payments.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VipNotification(Base):
    __tablename__ = "vip_notifications"
    __table_args__ = (
        UniqueConstraint(
            "telegram_user_id",
            "notification_key",
            name="uq_vip_notification_once",
        ),
        Index("ix_vip_notification_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_key: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
