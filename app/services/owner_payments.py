import json
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import OwnerAuditLog, utc_now
from app.repositories.billing import BillingRepository
from app.repositories.owner_revenue import OwnerRevenueRepository


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class OwnerPaymentService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._revenue = OwnerRevenueRepository(session_factory)
        self._billing = BillingRepository(session_factory)

    async def refund(
        self,
        bot: Bot,
        *,
        owner_user_id: int,
        payment_id: int,
        reason: str,
        confirmation: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        normalized_reason = reason.strip()
        if len(normalized_reason) < 5:
            raise ValueError("Причина повернення має містити щонайменше 5 символів.")
        current = _as_utc(now or utc_now())
        eligibility = await self._revenue.refund_eligibility(payment_id, now=current)
        if not eligibility["eligible"]:
            raise ValueError(eligibility["reason"])
        expected = f"ПОВЕРНУТИ {eligibility['stars']} STARS"
        if confirmation.strip() != expected:
            raise ValueError(f"Введи підтвердження: {expected}")

        await self._audit(
            owner_user_id,
            "payment.refund_requested",
            payment_id,
            {"stars": eligibility["stars"], "reason": normalized_reason},
            current,
        )
        try:
            await bot.refund_star_payment(
                user_id=eligibility["user_id"],
                telegram_payment_charge_id=eligibility["charge_id"],
            )
        except Exception as error:
            await self._audit(
                owner_user_id,
                "payment.refund_failed",
                payment_id,
                {"error_type": type(error).__name__},
                current,
            )
            raise RuntimeError("Telegram не підтвердив повернення Stars.") from error

        result = await self._revenue.apply_refund(
            payment_id,
            reason=normalized_reason,
            now=current,
        )
        await self._audit(
            owner_user_id,
            "payment.refunded",
            payment_id,
            {"stars": eligibility["stars"], "reason": normalized_reason},
            current,
        )
        if await self._billing.claim_notification(
            eligibility["user_id"],
            f"owner_refund:{eligibility['charge_id']}"[:160],
        ):
            await bot.send_message(
                eligibility["user_id"],
                "↩️ <b>Telegram Stars повернено</b>\n\n"
                f"ChatPulse повернув <b>{eligibility['stars']} ⭐</b>. "
                "VIP-статус перераховано без зміни інших покупок.",
                parse_mode="HTML",
            )
        return result

    async def set_subscription_state(
        self,
        bot: Bot,
        *,
        owner_user_id: int,
        user_id: int,
        canceled: bool,
        reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        normalized_reason = reason.strip()
        if len(normalized_reason) < 3:
            raise ValueError("Вкажи причину зміни підписки.")
        control = await self._billing.get_subscription_control(user_id)
        if control is None:
            raise LookupError("Активну місячну підписку не знайдено.")
        await bot.edit_user_star_subscription(
            user_id=user_id,
            telegram_payment_charge_id=control["telegram_payment_charge_id"],
            is_canceled=canceled,
        )
        await self._billing.set_subscription_canceled(user_id, canceled=canceled)
        action = "subscription.canceled_by_owner" if canceled else "subscription.restored_by_owner"
        current = _as_utc(now or utc_now())
        await self._audit(
            owner_user_id,
            action,
            control["invoice_intent_id"],
            {"user_id": user_id, "reason": normalized_reason},
            current,
        )
        return {"ok": True, "canceled": canceled}

    async def audit_note(
        self,
        *,
        owner_user_id: int,
        payment_id: int,
        user_id: int,
        now: datetime | None = None,
    ) -> None:
        await self._audit(
            owner_user_id,
            "payment.note_updated",
            payment_id,
            {"user_id": user_id},
            _as_utc(now or utc_now()),
        )

    async def _audit(
        self,
        owner_user_id: int,
        action: str,
        target_id: int,
        metadata: dict[str, Any],
        created_at: datetime,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            session.add(
                OwnerAuditLog(
                    owner_telegram_user_id=owner_user_id,
                    action=action,
                    target_type="payment",
                    target_id=str(target_id),
                    metadata_json=json.dumps(metadata, ensure_ascii=False),
                    created_at=created_at,
                )
            )
