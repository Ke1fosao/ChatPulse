from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.billing_models import VipInvoiceIntent, VipPayment
from app.vip_product_models import VipProductEvent
from app.models import User, VipGrant, utc_now
from app.owner_revenue_models import OwnerPaymentNote


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _display_name(user: User) -> str:
    return " ".join(part for part in (user.first_name, user.last_name) if part).strip() or str(
        user.telegram_id
    )


class OwnerRevenueRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_summary(self, *, days: int = 30, now: datetime | None = None) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        start = current - timedelta(days=max(1, min(days, 366)))
        async with self._session_factory() as session:
            period_rows = list(
                (await session.scalars(select(VipPayment).where(VipPayment.paid_at >= start))).all()
            )
            all_paid = list(
                (
                    await session.scalars(
                        select(VipPayment)
                        .where(VipPayment.status == "paid")
                        .order_by(VipPayment.paid_at.asc())
                    )
                ).all()
            )
            active_grants = list(
                (
                    await session.scalars(
                        select(VipGrant).where(
                            VipGrant.is_active.is_(True),
                            or_(VipGrant.expires_at.is_(None), VipGrant.expires_at > current),
                        )
                    )
                ).all()
            )
            intent_rows = list((await session.scalars(select(VipInvoiceIntent))).all())
            intents = {int(row.id): row for row in intent_rows}
            product_events = list((await session.scalars(select(VipProductEvent))).all())

        paid = [row for row in period_rows if row.status == "paid"]
        refunded = [row for row in period_rows if row.status == "refunded"]
        payer_ids = {int(row.telegram_user_id) for row in paid}
        recurring_users: set[int] = set()
        for row in all_paid:
            if row.product_code != "monthly_30d" or not row.granted_until:
                continue
            if _as_utc(row.granted_until) <= current:
                continue
            intent = intents.get(int(row.invoice_intent_id))
            if intent and intent.status != "canceled":
                recurring_users.add(int(row.telegram_user_id))

        trial_users = {
            int(row.telegram_user_id) for row in all_paid if row.product_code == "trial_7d"
        }
        converted_users = {
            user_id
            for user_id in trial_users
            if any(
                int(row.telegram_user_id) == user_id and row.product_code != "trial_7d"
                for row in all_paid
            )
        }
        active_paid = sum(1 for row in active_grants if int(row.granted_by_owner_id or 0) == 0)
        active_gifted = sum(1 for row in active_grants if int(row.granted_by_owner_id or 0) != 0)
        expiring_7d = sum(
            1
            for row in active_grants
            if row.expires_at and current < _as_utc(row.expires_at) <= current + timedelta(days=7)
        )
        stars = sum(int(row.stars_amount) for row in paid)
        stars_today = sum(
            int(row.stars_amount)
            for row in all_paid
            if _as_utc(row.paid_at).date() == current.date()
        )
        stars_7d = sum(
            int(row.stars_amount)
            for row in all_paid
            if _as_utc(row.paid_at) >= current - timedelta(days=7)
        )
        stars_30d = sum(
            int(row.stars_amount)
            for row in all_paid
            if _as_utc(row.paid_at) >= current - timedelta(days=30)
        )
        stars_all_time = sum(int(row.stars_amount) for row in all_paid)
        preview_users = {
            int(row.telegram_user_id)
            for row in product_events
            if row.event_type in {"vip_viewed", "vip_feature_previewed"}
            and _as_utc(row.created_at) >= start
        }
        trial_invoice_users = {
            int(row.telegram_user_id)
            for row in intent_rows
            if row.product_code == "trial_7d" and _as_utc(row.created_at) >= start
        }
        return {
            "period_days": days,
            "stars": stars,
            "stars_today": stars_today,
            "stars_7d": stars_7d,
            "stars_30d": stars_30d,
            "stars_all_time": stars_all_time,
            "payments": len(paid),
            "unique_payers": len(payer_ids),
            "average_payment": round(stars / len(paid), 2) if paid else 0,
            "arppu_stars": round(stars / len(payer_ids), 2) if payer_ids else 0,
            "active_paid_vip": active_paid,
            "active_gifted_vip": active_gifted,
            "active_subscriptions": len(recurring_users),
            "mrr_stars": len(recurring_users) * 59,
            "refunds": len(refunded),
            "refunded_stars": sum(int(row.stars_amount) for row in refunded),
            "expiring_7d": expiring_7d,
            "trial_previews": len(preview_users),
            "trial_invoices": len(trial_invoice_users),
            "trial_paid": len(trial_users),
            "trial_converted": len(converted_users),
            "trial_conversion_percent": round(len(converted_users) * 100 / len(trial_users), 1)
            if trial_users
            else 0,
        }

    async def get_timeline(
        self, *, days: int = 30, now: datetime | None = None
    ) -> list[dict[str, Any]]:
        current = _as_utc(now or utc_now())
        safe_days = max(1, min(days, 366))
        start_date = (current - timedelta(days=safe_days - 1)).date()
        async with self._session_factory() as session:
            rows = list(
                (
                    await session.scalars(
                        select(VipPayment).where(
                            VipPayment.paid_at
                            >= datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
                        )
                    )
                ).all()
            )
        buckets: dict[date, dict[str, int]] = defaultdict(
            lambda: {"gross_stars": 0, "refunded_stars": 0, "payments": 0}
        )
        for row in rows:
            bucket = buckets[_as_utc(row.paid_at).date()]
            if row.status == "paid":
                bucket["gross_stars"] += int(row.stars_amount)
                bucket["payments"] += 1
            elif row.status == "refunded":
                bucket["refunded_stars"] += int(row.stars_amount)
        return [
            {
                "date": (start_date + timedelta(days=index)).isoformat(),
                **buckets[start_date + timedelta(days=index)],
                "net_stars": buckets[start_date + timedelta(days=index)]["gross_stars"]
                - buckets[start_date + timedelta(days=index)]["refunded_stars"],
            }
            for index in range(safe_days)
        ]

    async def get_plan_distribution(
        self, *, days: int = 30, now: datetime | None = None
    ) -> list[dict[str, Any]]:
        current = _as_utc(now or utc_now())
        start = current - timedelta(days=max(1, min(days, 366)))
        async with self._session_factory() as session:
            rows = list(
                (
                    await session.scalars(
                        select(VipPayment).where(
                            VipPayment.paid_at >= start,
                            VipPayment.status == "paid",
                        )
                    )
                ).all()
            )
        buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"payments": 0, "stars": 0})
        for row in rows:
            bucket = buckets[row.product_code]
            bucket["payments"] += 1
            bucket["stars"] += int(row.stars_amount)
        return [
            {"product_code": code, **values}
            for code, values in sorted(
                buckets.items(), key=lambda item: item[1]["stars"], reverse=True
            )
        ]

    async def list_transactions(
        self,
        *,
        query: str | None = None,
        product_code: str | None = None,
        status: str | None = None,
        recurring: bool | None = None,
        days: int | None = None,
        limit: int = 50,
        offset: int = 0,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        statement = select(VipPayment, User).join(
            User, User.telegram_id == VipPayment.telegram_user_id
        )
        normalized = (query or "").strip().casefold()
        if normalized:
            pattern = f"%{normalized}%"
            statement = statement.where(
                or_(
                    func.lower(User.first_name).like(pattern),
                    func.lower(func.coalesce(User.last_name, "")).like(pattern),
                    func.lower(func.coalesce(User.username, "")).like(pattern),
                    cast(User.telegram_id, String).like(pattern),
                    func.lower(VipPayment.telegram_payment_charge_id).like(pattern),
                )
            )
        if product_code:
            statement = statement.where(VipPayment.product_code == product_code)
        if status:
            statement = statement.where(VipPayment.status == status)
        if recurring is not None:
            statement = statement.where(VipPayment.is_recurring.is_(recurring))
        if days:
            statement = statement.where(
                VipPayment.paid_at >= current - timedelta(days=min(days, 366))
            )

        async with self._session_factory() as session:
            total = int(
                await session.scalar(
                    select(func.count()).select_from(statement.order_by(None).subquery())
                )
                or 0
            )
            rows = (
                await session.execute(
                    statement.order_by(VipPayment.paid_at.desc(), VipPayment.id.desc())
                    .limit(min(max(limit, 1), 100))
                    .offset(max(offset, 0))
                )
            ).all()
        return {
            "items": [self._serialize_payment(payment, user) for payment, user in rows],
            "total": total,
        }

    async def get_transaction(self, payment_id: int) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    select(VipPayment, User)
                    .join(User, User.telegram_id == VipPayment.telegram_user_id)
                    .where(VipPayment.id == payment_id)
                )
            ).first()
            if row is None:
                return None
            payment, user = row
            note = await session.scalar(
                select(OwnerPaymentNote).where(OwnerPaymentNote.payment_id == payment_id)
            )
            history = (
                (
                    await session.execute(
                        select(VipPayment)
                        .where(VipPayment.telegram_user_id == payment.telegram_user_id)
                        .order_by(VipPayment.paid_at.desc())
                    )
                )
                .scalars()
                .all()
            )
            grant = await session.get(VipGrant, int(payment.telegram_user_id))
        payload = self._serialize_payment(payment, user)
        payload["note"] = self._serialize_note(note) if note else None
        payload["history"] = [self._serialize_payment(item, user) for item in history]
        payload["vip_grant"] = {
            "is_active": bool(grant and grant.is_active),
            "expires_at": _as_utc(grant.expires_at).isoformat()
            if grant and grant.expires_at
            else None,
            "granted_by_owner_id": int(grant.granted_by_owner_id or 0) if grant else None,
            "reason": grant.grant_reason if grant else None,
        }
        payload["refund"] = await self.refund_eligibility(payment_id)
        return payload

    async def save_note(
        self,
        *,
        owner_user_id: int,
        payment_id: int,
        user_id: int,
        text: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        normalized = text.strip()
        if not normalized or len(normalized) > 1000:
            raise ValueError("Примітка має містити від 1 до 1000 символів.")
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            payment = await session.get(VipPayment, payment_id)
            if payment is None or int(payment.telegram_user_id) != user_id:
                raise LookupError("Payment not found")
            note = await session.scalar(
                select(OwnerPaymentNote).where(OwnerPaymentNote.payment_id == payment_id)
            )
            if note is None:
                note = OwnerPaymentNote(
                    owner_telegram_user_id=owner_user_id,
                    payment_id=payment_id,
                    telegram_user_id=user_id,
                    note_text=normalized,
                    created_at=current,
                    updated_at=current,
                )
                session.add(note)
            else:
                note.owner_telegram_user_id = owner_user_id
                note.note_text = normalized
                note.updated_at = current
            await session.flush()
            return self._serialize_note(note)

    async def refund_eligibility(
        self,
        payment_id: int,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session:
            payment = await session.get(VipPayment, payment_id)
            if payment is None:
                return {"eligible": False, "reason": "Платіж не знайдено."}
            if payment.status != "paid":
                return {"eligible": False, "reason": "Платіж уже не має статусу paid."}
            latest = await session.scalar(
                select(VipPayment)
                .where(
                    VipPayment.telegram_user_id == payment.telegram_user_id,
                    VipPayment.status == "paid",
                )
                .order_by(VipPayment.paid_at.desc(), VipPayment.id.desc())
            )
            if latest is None or int(latest.id) != int(payment.id):
                return {
                    "eligible": False,
                    "reason": "Повернути можна лише останню активну покупку.",
                }
            grant = await session.get(VipGrant, int(payment.telegram_user_id))
            if grant and int(grant.granted_by_owner_id or 0) != 0:
                return {"eligible": False, "reason": "Поточний VIP був подарований власником."}
            if grant and payment.granted_until and grant.expires_at:
                if (
                    abs(
                        (_as_utc(grant.expires_at) - _as_utc(payment.granted_until)).total_seconds()
                    )
                    > 60
                ):
                    return {"eligible": False, "reason": "VIP-період уже змінено іншою операцією."}
            return {
                "eligible": True,
                "reason": "",
                "user_id": int(payment.telegram_user_id),
                "charge_id": payment.telegram_payment_charge_id,
                "stars": int(payment.stars_amount),
                "product_code": payment.product_code,
                "active_until": _as_utc(payment.granted_until).isoformat()
                if payment.granted_until
                else None,
                "is_active": bool(
                    payment.granted_until and _as_utc(payment.granted_until) > current
                ),
            }

    async def apply_refund(
        self,
        payment_id: int,
        *,
        reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        eligibility = await self.refund_eligibility(payment_id, now=current)
        if not eligibility["eligible"]:
            raise ValueError(eligibility["reason"])
        async with self._session_factory() as session, session.begin():
            payment = await session.get(VipPayment, payment_id)
            assert payment is not None
            payment.status = "refunded"
            payment.refunded_at = current
            payment.refund_reason = reason[:255]
            previous = await session.scalar(
                select(VipPayment)
                .where(
                    VipPayment.telegram_user_id == payment.telegram_user_id,
                    VipPayment.status == "paid",
                    VipPayment.id != payment.id,
                )
                .order_by(VipPayment.granted_until.desc(), VipPayment.id.desc())
            )
            grant = await session.get(VipGrant, int(payment.telegram_user_id))
            if grant is not None:
                previous_until = (
                    _as_utc(previous.granted_until) if previous and previous.granted_until else None
                )
                if previous_until and previous_until > current:
                    grant.is_active = True
                    grant.expires_at = previous_until
                    grant.grant_reason = f"Telegram Stars · {previous.product_code}"
                    grant.granted_by_owner_id = 0
                else:
                    grant.is_active = False
                    grant.expires_at = current
                    grant.revoke_reason = "payment_refunded"
                    grant.revoked_at = current
                grant.updated_at = current
        return {"ok": True, "payment_id": payment_id, "status": "refunded"}

    async def export_csv(self, **filters: Any) -> bytes:
        offset = 0
        rows: list[dict[str, Any]] = []
        while True:
            page = await self.list_transactions(limit=100, offset=offset, **filters)
            rows.extend(page["items"])
            offset += len(page["items"])
            if offset >= page["total"] or not page["items"]:
                break
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "paid_at",
                "telegram_user_id",
                "username",
                "product_code",
                "stars",
                "status",
                "recurring",
                "granted_until",
                "refunded_at",
                "charge_id",
            ]
        )
        for item in rows:
            writer.writerow(
                [
                    item["paid_at"],
                    item["telegram_user_id"],
                    item.get("username") or "",
                    item["product_code"],
                    item["stars_amount"],
                    item["status"],
                    item["is_recurring"],
                    item.get("granted_until") or "",
                    item.get("refunded_at") or "",
                    item["telegram_payment_charge_id"],
                ]
            )
        return buffer.getvalue().encode("utf-8-sig")

    @staticmethod
    def _serialize_payment(payment: VipPayment, user: User) -> dict[str, Any]:
        return {
            "id": int(payment.id),
            "telegram_user_id": int(payment.telegram_user_id),
            "display_name": _display_name(user),
            "username": user.username,
            "product_code": payment.product_code,
            "stars_amount": int(payment.stars_amount),
            "status": payment.status,
            "is_recurring": bool(payment.is_recurring),
            "is_first_recurring": bool(payment.is_first_recurring),
            "paid_at": _as_utc(payment.paid_at).isoformat(),
            "granted_until": _as_utc(payment.granted_until).isoformat()
            if payment.granted_until
            else None,
            "subscription_expiration_date": _as_utc(
                payment.subscription_expiration_date
            ).isoformat()
            if payment.subscription_expiration_date
            else None,
            "refunded_at": _as_utc(payment.refunded_at).isoformat()
            if payment.refunded_at
            else None,
            "refund_reason": payment.refund_reason,
            "telegram_payment_charge_id": payment.telegram_payment_charge_id,
        }

    @staticmethod
    def _serialize_note(note: OwnerPaymentNote) -> dict[str, Any]:
        return {
            "id": int(note.id),
            "owner_telegram_user_id": int(note.owner_telegram_user_id),
            "payment_id": int(note.payment_id),
            "telegram_user_id": int(note.telegram_user_id),
            "text": note.note_text,
            "created_at": _as_utc(note.created_at).isoformat(),
            "updated_at": _as_utc(note.updated_at).isoformat(),
        }
