from .base import *  # noqa: F403
from .base import _as_utc, _display_name, _level_for_xp, _active_vip_clause


class UserMessagingMixin:
    async def create_message_delivery(
        self,
        actor: AdminActor,
        user_id: int,
        message_text: str,
    ) -> dict[str, Any]:
        actor.require("users.message")
        normalized = message_text.strip()
        if not 1 <= len(normalized) <= 1000:
            raise ValueError("Повідомлення має містити від 1 до 1000 символів.")
        current = _as_utc(utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_user(session, user_id)
            delivery = AdminMessageDelivery(
                telegram_user_id=user_id,
                actor_telegram_user_id=actor.telegram_user_id,
                message_text=normalized,
                status="pending",
                created_at=current,
            )
            session.add(delivery)
            await session.flush()
            return self._serialize_delivery(delivery)

    async def finish_message_delivery(
        self,
        actor: AdminActor,
        delivery_id: int,
        *,
        sent: bool,
        safe_error: str | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(utc_now())
        async with self._session_factory() as session, session.begin():
            delivery = await session.get(AdminMessageDelivery, delivery_id)
            if delivery is None:
                raise LookupError("Запис доставки не знайдено.")
            delivery.status = "sent" if sent else "failed"
            delivery.safe_error = (safe_error or "")[:500] or None
            delivery.sent_at = current if sent else None
            session.add(
                self._audit_entry(
                    actor,
                    action="user.message_sent" if sent else "user.message_failed",
                    target_id=int(delivery.telegram_user_id),
                    metadata={"delivery_id": delivery_id, "safe_error": delivery.safe_error},
                    created_at=current,
                )
            )
            await session.flush()
            return self._serialize_delivery(delivery)
