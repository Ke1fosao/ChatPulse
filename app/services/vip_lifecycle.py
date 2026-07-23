from datetime import UTC, datetime, timedelta

from aiogram import Bot
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import VipGrant, utc_now
from app.repositories.billing import BillingRepository


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class VipLifecycleService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._billing = BillingRepository(session_factory)

    async def send_due(self, bot: Bot, *, now: datetime | None = None) -> dict[str, int]:
        current = _as_utc(now or utc_now())
        warning_until = current + timedelta(days=3)
        expired_since = current - timedelta(days=7)
        async with self._session_factory() as session:
            warning_rows = list(
                (
                    await session.scalars(
                        select(VipGrant).where(
                            VipGrant.is_active.is_(True),
                            VipGrant.expires_at.is_not(None),
                            VipGrant.expires_at > current,
                            VipGrant.expires_at <= warning_until,
                        )
                    )
                ).all()
            )
            expired_rows = list(
                (
                    await session.scalars(
                        select(VipGrant).where(
                            VipGrant.expires_at.is_not(None),
                            VipGrant.expires_at <= current,
                            VipGrant.expires_at >= expired_since,
                            or_(
                                VipGrant.is_active.is_(True),
                                and_(
                                    VipGrant.revoked_at.is_(None),
                                    VipGrant.revoke_reason.is_(None),
                                ),
                            ),
                        )
                    )
                ).all()
            )

        warning_sent = 0
        for grant in warning_rows:
            assert grant.expires_at is not None
            expiry = _as_utc(grant.expires_at)
            key = f"vip_expiry_warning:{expiry.date().isoformat()}"
            if not await self._billing.claim_notification(int(grant.telegram_user_id), key):
                continue
            await bot.send_message(
                int(grant.telegram_user_id),
                "👑 <b>ChatPulse VIP скоро завершиться</b>\n\n"
                f"Доступ діє до <b>{expiry.astimezone().strftime('%d.%m.%Y %H:%M')}</b>.\n"
                "Продовжити VIP можна у профілі ChatPulse.",
                parse_mode="HTML",
            )
            warning_sent += 1

        expired_sent = 0
        for grant in expired_rows:
            assert grant.expires_at is not None
            expiry = _as_utc(grant.expires_at)
            key = f"vip_expired:{expiry.date().isoformat()}"
            if not await self._billing.claim_notification(int(grant.telegram_user_id), key):
                continue
            await bot.send_message(
                int(grant.telegram_user_id),
                "🔒 <b>ChatPulse VIP завершився</b>\n\n"
                "Твій прогрес і статистика збережені. Premium-функції можна знову "
                "відкрити у профілі ChatPulse.",
                parse_mode="HTML",
            )
            expired_sent += 1

        return {"warning_sent": warning_sent, "expired_sent": expired_sent}

    async def notify_subscription_state(
        self,
        bot: Bot,
        *,
        user_id: int,
        charge_id: str,
        canceled: bool,
    ) -> bool:
        state = "canceled" if canceled else "restored"
        key = f"subscription_{state}:{charge_id}"[:160]
        if not await self._billing.claim_notification(user_id, key):
            return False
        text = (
            "⏸ <b>Автопродовження VIP вимкнено</b>\n\n"
            "Поточний оплачений період продовжує діяти до своєї дати завершення."
            if canceled
            else "▶️ <b>Автопродовження VIP відновлено</b>\n\n"
            "Наступний 30-денний період буде оплачено Telegram Stars автоматично."
        )
        await bot.send_message(user_id, text, parse_mode="HTML")
        return True
