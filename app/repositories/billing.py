from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.billing_models import VipInvoiceIntent, VipPayment, VipTrialClaim
from app.models import User, VipGrant, utc_now
from app.services.vip_plans import VIPPlan, get_vip_plan, new_invoice_payload


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class PaymentResult:
    status: str
    payment_id: int
    product_code: str
    expires_at: datetime | None
    refund_required: bool = False


class BillingRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def trial_available(self, user_id: int, *, now: datetime | None = None) -> bool:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session:
            return await self._trial_available(session, user_id, current=current)

    async def create_invoice_intent(
        self,
        user_id: int,
        product_code: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        plan = get_vip_plan(product_code)
        async with self._session_factory() as session, session.begin():
            if await session.get(User, user_id) is None:
                raise LookupError("User is not registered")
            if plan.code == "trial_7d" and not await self._trial_available(
                session,
                user_id,
                current=current,
            ):
                raise ValueError("Пробний VIP уже використано або VIP зараз активний.")
            if plan.recurring and await self._has_active_monthly_subscription(
                session,
                user_id,
                current=current,
            ):
                raise ValueError("Місячна VIP-підписка вже активна.")

            intent = VipInvoiceIntent(
                payload=new_invoice_payload(plan.code),
                telegram_user_id=user_id,
                product_code=plan.code,
                stars_amount=plan.stars,
                is_recurring=plan.recurring,
                status="open",
                created_at=current,
            )
            session.add(intent)
            await session.flush()
            return self._serialize_intent(intent, plan)

    async def invalidate_invoice(self, payload: str, *, now: datetime | None = None) -> None:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            intent = await session.scalar(
                select(VipInvoiceIntent).where(VipInvoiceIntent.payload == payload)
            )
            if intent is not None:
                intent.status = "invalid"
                intent.invalidated_at = current

    async def validate_checkout(
        self,
        *,
        user_id: int,
        payload: str,
        currency: str,
        total_amount: int,
        now: datetime | None = None,
    ) -> tuple[bool, str]:
        current = _as_utc(now or utc_now())
        if currency != "XTR":
            return False, "ChatPulse VIP оплачується лише Telegram Stars."
        async with self._session_factory() as session:
            intent = await session.scalar(
                select(VipInvoiceIntent).where(VipInvoiceIntent.payload == payload)
            )
            if intent is None or intent.status not in {"open", "canceled"}:
                return False, "Рахунок застарів. Створи новий у ChatPulse."
            if int(intent.telegram_user_id) != user_id:
                return False, "Цей рахунок створено для іншого користувача."
            if int(intent.stars_amount) != total_amount:
                return False, "Сума рахунку не збігається."
            if intent.product_code == "trial_7d" and not await self._trial_available(
                session,
                user_id,
                current=current,
            ):
                return False, "Пробний VIP уже використано або VIP зараз активний."
            return True, ""

    async def record_payment(
        self,
        *,
        user_id: int,
        payload: str,
        currency: str,
        total_amount: int,
        telegram_payment_charge_id: str,
        provider_payment_charge_id: str | None,
        is_recurring: bool,
        is_first_recurring: bool,
        subscription_expiration_date: int | None,
        now: datetime | None = None,
    ) -> PaymentResult:
        current = _as_utc(now or utc_now())
        if currency != "XTR":
            raise ValueError("Unsupported payment currency")

        async with self._session_factory() as session, session.begin():
            existing = await session.scalar(
                select(VipPayment).where(
                    VipPayment.telegram_payment_charge_id == telegram_payment_charge_id
                )
            )
            if existing is not None:
                return PaymentResult(
                    status="duplicate",
                    payment_id=int(existing.id),
                    product_code=existing.product_code,
                    expires_at=(
                        _as_utc(existing.granted_until) if existing.granted_until else None
                    ),
                    refund_required=existing.status == "refund_required",
                )

            intent = await session.scalar(
                select(VipInvoiceIntent).where(VipInvoiceIntent.payload == payload)
            )
            if intent is None:
                raise LookupError("Unknown invoice payload")
            if int(intent.telegram_user_id) != user_id:
                raise PermissionError("Invoice user mismatch")
            if int(intent.stars_amount) != total_amount:
                raise ValueError("Invoice amount mismatch")

            plan = get_vip_plan(intent.product_code)
            if plan.recurring != bool(is_recurring or is_first_recurring):
                raise ValueError("Recurring payment flags do not match the product")

            subscription_expiry = (
                datetime.fromtimestamp(subscription_expiration_date, tz=UTC)
                if subscription_expiration_date is not None
                else None
            )
            if plan.recurring and subscription_expiry is None:
                raise ValueError("Recurring payment has no subscription expiry")

            payment = VipPayment(
                invoice_intent_id=int(intent.id),
                telegram_user_id=user_id,
                product_code=plan.code,
                stars_amount=plan.stars,
                telegram_payment_charge_id=telegram_payment_charge_id,
                provider_payment_charge_id=provider_payment_charge_id,
                is_recurring=bool(is_recurring),
                is_first_recurring=bool(is_first_recurring),
                subscription_expiration_date=subscription_expiry,
                status="paid",
                paid_at=current,
            )
            session.add(payment)
            await session.flush()

            if plan.code == "trial_7d":
                claim_created = True
                try:
                    async with session.begin_nested():
                        session.add(
                            VipTrialClaim(
                                telegram_user_id=user_id,
                                payment_id=int(payment.id),
                                claimed_at=current,
                            )
                        )
                        await session.flush()
                except IntegrityError:
                    claim_created = False
                if not claim_created:
                    payment.status = "refund_required"
                    payment.refund_reason = "duplicate_trial"
                    return PaymentResult(
                        status="duplicate_trial",
                        payment_id=int(payment.id),
                        product_code=plan.code,
                        expires_at=None,
                        refund_required=True,
                    )

            expires_at = await self._grant_paid_vip(
                session,
                user_id=user_id,
                plan=plan,
                subscription_expiry=subscription_expiry,
                current=current,
            )
            payment.granted_until = expires_at
            if plan.recurring:
                intent.status = "open"
            else:
                intent.status = "paid"
            await session.flush()
            return PaymentResult(
                status="granted",
                payment_id=int(payment.id),
                product_code=plan.code,
                expires_at=expires_at,
            )

    async def mark_refunded(
        self,
        payment_id: int,
        *,
        reason: str,
        now: datetime | None = None,
    ) -> None:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            payment = await session.get(VipPayment, payment_id)
            if payment is None:
                raise LookupError("Payment not found")
            payment.status = "refunded"
            payment.refunded_at = current
            payment.refund_reason = reason[:255]

    async def get_status(self, user_id: int, *, now: datetime | None = None) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session:
            grant = await session.get(VipGrant, user_id)
            active = bool(
                grant
                and grant.is_active
                and (grant.expires_at is None or _as_utc(grant.expires_at) > current)
            )
            subscription = await self._active_subscription(session, user_id, current=current)
            return {
                "is_vip": active,
                "vip_expires_at": (
                    _as_utc(grant.expires_at).isoformat()
                    if active and grant and grant.expires_at
                    else None
                ),
                "trial_available": await self._trial_available(
                    session,
                    user_id,
                    current=current,
                ),
                "active_subscription": subscription,
            }

    async def list_history(self, user_id: int, *, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = min(max(limit, 1), 50)
        async with self._session_factory() as session:
            rows = list(
                (
                    await session.scalars(
                        select(VipPayment)
                        .where(VipPayment.telegram_user_id == user_id)
                        .order_by(VipPayment.paid_at.desc(), VipPayment.id.desc())
                        .limit(safe_limit)
                    )
                ).all()
            )
            return [self._serialize_payment(row) for row in rows]

    async def get_subscription_control(self, user_id: int) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            first_payment = await session.scalar(
                select(VipPayment)
                .where(
                    VipPayment.telegram_user_id == user_id,
                    VipPayment.product_code == "monthly_30d",
                    VipPayment.status == "paid",
                )
                .order_by(VipPayment.is_first_recurring.desc(), VipPayment.paid_at.asc())
            )
            if first_payment is None:
                return None
            intent = await session.get(VipInvoiceIntent, first_payment.invoice_intent_id)
            return {
                "telegram_payment_charge_id": first_payment.telegram_payment_charge_id,
                "is_canceled": bool(intent and intent.status == "canceled"),
                "invoice_intent_id": int(first_payment.invoice_intent_id),
            }

    async def set_subscription_canceled(
        self,
        user_id: int,
        *,
        canceled: bool,
    ) -> None:
        control = await self.get_subscription_control(user_id)
        if control is None:
            raise LookupError("Active subscription not found")
        async with self._session_factory() as session, session.begin():
            intent = await session.get(VipInvoiceIntent, control["invoice_intent_id"])
            if intent is None or int(intent.telegram_user_id) != user_id:
                raise LookupError("Subscription invoice not found")
            intent.status = "canceled" if canceled else "open"

    async def claim_notification(self, user_id: int, notification_key: str) -> bool:
        from app.billing_models import VipNotification

        async with self._session_factory() as session, session.begin():
            try:
                async with session.begin_nested():
                    session.add(
                        VipNotification(
                            telegram_user_id=user_id,
                            notification_key=notification_key[:160],
                        )
                    )
                    await session.flush()
                return True
            except IntegrityError:
                return False

    async def _grant_paid_vip(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        plan: VIPPlan,
        subscription_expiry: datetime | None,
        current: datetime,
    ) -> datetime:
        grant = await session.get(VipGrant, user_id)
        if plan.recurring:
            assert subscription_expiry is not None
            expires_at = _as_utc(subscription_expiry)
        else:
            existing_expiry = (
                _as_utc(grant.expires_at)
                if grant and grant.is_active and grant.expires_at and _as_utc(grant.expires_at) > current
                else current
            )
            expires_at = existing_expiry + timedelta(days=plan.duration_days)

        if grant is None:
            grant = VipGrant(
                telegram_user_id=user_id,
                created_at=current,
            )
            session.add(grant)
        if not grant.is_active or (grant.expires_at and _as_utc(grant.expires_at) <= current):
            grant.starts_at = current
        grant.is_active = True
        grant.expires_at = expires_at
        grant.granted_by_owner_id = 0
        grant.grant_reason = f"Telegram Stars · {plan.code}"
        grant.revoked_at = None
        grant.revoked_by_owner_id = None
        grant.revoke_reason = None
        grant.updated_at = current
        return expires_at

    async def _trial_available(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        current: datetime,
    ) -> bool:
        if await session.get(VipTrialClaim, user_id) is not None:
            return False
        grant = await session.get(VipGrant, user_id)
        if grant and grant.is_active and (
            grant.expires_at is None or _as_utc(grant.expires_at) > current
        ):
            return False
        paid_count = int(
            await session.scalar(
                select(func.count())
                .select_from(VipPayment)
                .where(
                    VipPayment.telegram_user_id == user_id,
                    VipPayment.status == "paid",
                )
            )
            or 0
        )
        return paid_count == 0

    async def _has_active_monthly_subscription(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        current: datetime,
    ) -> bool:
        row = await session.scalar(
            select(VipPayment.id).where(
                VipPayment.telegram_user_id == user_id,
                VipPayment.product_code == "monthly_30d",
                VipPayment.status == "paid",
                VipPayment.granted_until > current,
            )
        )
        return row is not None

    async def _active_subscription(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        current: datetime,
    ) -> dict[str, Any] | None:
        payment = await session.scalar(
            select(VipPayment)
            .where(
                VipPayment.telegram_user_id == user_id,
                VipPayment.product_code == "monthly_30d",
                VipPayment.status == "paid",
                VipPayment.granted_until > current,
            )
            .order_by(VipPayment.paid_at.desc())
        )
        if payment is None:
            return None
        intent = await session.get(VipInvoiceIntent, payment.invoice_intent_id)
        return {
            "product_code": payment.product_code,
            "expires_at": _as_utc(payment.granted_until).isoformat(),
            "is_canceled": bool(intent and intent.status == "canceled"),
        }

    @staticmethod
    def _serialize_intent(intent: VipInvoiceIntent, plan: VIPPlan) -> dict[str, Any]:
        return {
            "id": int(intent.id),
            "payload": intent.payload,
            "telegram_user_id": int(intent.telegram_user_id),
            "product_code": plan.code,
            "stars": plan.stars,
            "recurring": plan.recurring,
            "subscription_period": plan.subscription_period,
            "title": plan.title,
            "description": plan.description,
        }

    @staticmethod
    def _serialize_payment(payment: VipPayment) -> dict[str, Any]:
        return {
            "id": int(payment.id),
            "product_code": payment.product_code,
            "stars_amount": int(payment.stars_amount),
            "status": payment.status,
            "is_recurring": bool(payment.is_recurring),
            "is_first_recurring": bool(payment.is_first_recurring),
            "paid_at": _as_utc(payment.paid_at).isoformat(),
            "granted_until": (
                _as_utc(payment.granted_until).isoformat() if payment.granted_until else None
            ),
            "refunded_at": (
                _as_utc(payment.refunded_at).isoformat() if payment.refunded_at else None
            ),
        }
