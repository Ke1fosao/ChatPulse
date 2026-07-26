# ruff: noqa: F401, F403, F405, F821, I001
from .base import *  # noqa: F403
from .base import _as_utc, _display_name, _level_for_xp, _active_vip_clause


class UserRestrictionsMixin:
    async def is_blocked(self, telegram_user_id: int) -> bool:
        async with self._session_factory() as session:
            restriction = await session.get(UserRestriction, telegram_user_id)
            return bool(restriction and restriction.is_blocked)

    async def get_block_info(self, telegram_user_id: int) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            restriction = await session.get(UserRestriction, telegram_user_id)
            if restriction is None or not restriction.is_blocked:
                return None
            return {
                "is_blocked": True,
                "reason": restriction.reason,
                "blocked_at": (
                    _as_utc(restriction.blocked_at).isoformat() if restriction.blocked_at else None
                ),
            }

    async def record_blocked_access(
        self,
        telegram_user_id: int,
        source: Literal["miniapp", "bot_private", "bot_group"],
        *,
        now: datetime | None = None,
    ) -> None:
        current = _as_utc(now or utc_now())
        bucket_minute = (current.minute // 10) * 10
        window_key = current.replace(minute=bucket_minute, second=0, microsecond=0).strftime(
            "%Y%m%d%H%M"
        )
        async with self._session_factory() as session, session.begin():
            event = (
                await session.scalars(
                    select(BlockedAccessEvent).where(
                        BlockedAccessEvent.telegram_user_id == telegram_user_id,
                        BlockedAccessEvent.source == source,
                        BlockedAccessEvent.window_key == window_key,
                    )
                )
            ).first()
            if event is None:
                session.add(
                    BlockedAccessEvent(
                        telegram_user_id=telegram_user_id,
                        source=source,
                        window_key=window_key,
                        first_attempt_at=current,
                        last_attempt_at=current,
                    )
                )
            else:
                event.attempt_count += 1
                event.last_attempt_at = current

    async def block_user(
        self,
        actor: AdminActor,
        target_user_id: int,
        reason: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        actor.require("users.block")
        normalized_reason = self._reason(reason)
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_mutable_target(session, target_user_id)
            restriction = await session.get(UserRestriction, target_user_id)
            if restriction is None:
                restriction = UserRestriction(telegram_user_id=target_user_id)
                session.add(restriction)
            if restriction.is_blocked:
                raise ValueError("Користувач уже заблокований.")
            restriction.is_blocked = True
            restriction.reason = normalized_reason
            restriction.blocked_by_actor_id = actor.telegram_user_id
            restriction.blocked_at = current
            restriction.unblocked_by_actor_id = None
            restriction.unblocked_at = None
            restriction.unblock_reason = None
            restriction.updated_at = current
            session.add(
                self._audit_entry(
                    actor,
                    action="user.blocked",
                    target_id=target_user_id,
                    metadata={"reason": normalized_reason},
                    created_at=current,
                )
            )
            await session.flush()
            return self._serialize_restriction(restriction)

    async def unblock_user(
        self,
        actor: AdminActor,
        target_user_id: int,
        reason: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        actor.require("users.block")
        normalized_reason = self._reason(reason)
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_mutable_target(session, target_user_id)
            restriction = await session.get(UserRestriction, target_user_id)
            if restriction is None or not restriction.is_blocked:
                raise ValueError("Користувач не заблокований.")
            restriction.is_blocked = False
            restriction.unblocked_by_actor_id = actor.telegram_user_id
            restriction.unblocked_at = current
            restriction.unblock_reason = normalized_reason
            restriction.updated_at = current
            session.add(
                self._audit_entry(
                    actor,
                    action="user.unblocked",
                    target_id=target_user_id,
                    metadata={"reason": normalized_reason},
                    created_at=current,
                )
            )
            await session.flush()
            return self._serialize_restriction(restriction)
