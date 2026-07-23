from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.types import Message, PreCheckoutQuery

from app.repositories.billing import BillingRepository
from app.services.vip_plans import get_vip_plan

router = Router(name="payments")


@router.pre_checkout_query()
async def vip_pre_checkout(
    query: PreCheckoutQuery,
    billing_repository: BillingRepository,
) -> None:
    ok, error_message = await billing_repository.validate_checkout(
        user_id=query.from_user.id,
        payload=query.invoice_payload,
        currency=query.currency,
        total_amount=query.total_amount,
    )
    await query.answer(ok=ok, error_message=error_message or None)


@router.message(F.successful_payment)
async def vip_successful_payment(
    message: Message,
    bot: Bot,
    billing_repository: BillingRepository,
) -> None:
    user = message.from_user
    payment = message.successful_payment
    if user is None or payment is None:
        return

    result = await billing_repository.record_payment(
        user_id=user.id,
        payload=payment.invoice_payload,
        currency=payment.currency,
        total_amount=payment.total_amount,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id or None,
        is_recurring=bool(payment.is_recurring),
        is_first_recurring=bool(payment.is_first_recurring),
        subscription_expiration_date=payment.subscription_expiration_date,
    )

    if result.refund_required:
        await bot.refund_star_payment(
            user_id=user.id,
            telegram_payment_charge_id=payment.telegram_payment_charge_id,
        )
        await billing_repository.mark_refunded(
            result.payment_id,
            reason="Пробний VIP уже був використаний. Автоматичне повернення 1 ⭐.",
        )
        await message.answer(
            "↩️ Пробний VIP уже був використаний раніше, тому 1 ⭐ автоматично повернено."
        )
        return

    if result.status == "duplicate":
        return

    plan = get_vip_plan(result.product_code)
    expiry = _format_expiry(result.expires_at)
    renewal = (
        "Підписка автоматично продовжуватиметься кожні 30 днів. "
        "Її можна скасувати у VIP-розділі Mini App."
        if plan.recurring
        else "Автоматичного продовження немає."
    )
    await message.answer(
        "👑 <b>ChatPulse VIP активовано!</b>\n\n"
        f"Тариф: <b>{plan.short_title}</b>\n"
        f"Сплачено: <b>{plan.stars} ⭐</b>\n"
        f"Діє до: <b>{expiry}</b>\n\n"
        f"{renewal}",
        parse_mode="HTML",
    )


def _format_expiry(value: datetime | None) -> str:
    if value is None:
        return "безстроково"
    return value.astimezone().strftime("%d.%m.%Y %H:%M")
