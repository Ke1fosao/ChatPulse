# ruff: noqa: F401, F403, F405, F821, I001
from .base import *  # noqa: F403
from .base import _as_utc, _display_name, _level_for_xp, _active_vip_clause


class UserXpMixin:
    async def adjust_xp(
        self,
        actor: AdminActor,
        user_id: int,
        amount: int,
        reason: str,
        *,
        chat_id: int | None = None,
    ) -> dict[str, Any]:
        actor.require("xp.manage")
        if amount == 0 or abs(amount) > 100_000:
            raise ValueError("Зміна XP має бути від 1 до 100000 за модулем.")
        normalized_reason = self._reason(reason)
        current = _as_utc(utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_mutable_target(session, user_id)
            if chat_id is None:
                user = await self._require_user(session, user_id)
                previous = int(user.global_xp_total)
                resulting = previous + amount
                if resulting < 0:
                    raise ValueError("XP не може стати від’ємним.")
                user.global_xp_total = resulting
                user.global_level = _level_for_xp(resulting)
                level = int(user.global_level)
            else:
                member = await session.get(GroupMember, (chat_id, user_id))
                if member is None:
                    raise LookupError("Користувач не входить до вибраної групи.")
                previous = int(member.xp_total)
                resulting = previous + amount
                if resulting < 0:
                    raise ValueError("XP не може стати від’ємним.")
                member.xp_total = resulting
                member.level = _level_for_xp(resulting)
                level = int(member.level)
            adjustment = UserXpAdjustment(
                telegram_user_id=user_id,
                telegram_chat_id=chat_id,
                amount=amount,
                previous_total=previous,
                resulting_total=resulting,
                reason=normalized_reason,
                actor_telegram_user_id=actor.telegram_user_id,
                created_at=current,
            )
            session.add(adjustment)
            session.add(
                self._audit_entry(
                    actor,
                    action="user.xp_adjusted",
                    target_id=user_id,
                    metadata={
                        "chat_id": chat_id,
                        "amount": amount,
                        "previous_total": previous,
                        "resulting_total": resulting,
                        "reason": normalized_reason,
                    },
                    created_at=current,
                )
            )
            await session.flush()
            return {
                "id": int(adjustment.id),
                "telegram_user_id": user_id,
                "telegram_chat_id": chat_id,
                "amount": amount,
                "previous_total": previous,
                "resulting_total": resulting,
                "level": level,
                "created_at": current.isoformat(),
            }
