import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import BotOwner, OwnerAuditLog, User, VipGrant, utc_now
from app.repositories.owner import OWNER_KEY
from app.services.admin_access import AdminActor


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class AdminVipService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def grant(
        self,
        actor: AdminActor,
        target_user_id: int,
        *,
        expires_at: datetime | None,
        reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        actor.require("vip.manage")
        current = _as_utc(now or utc_now())
        normalized_expiry = _as_utc(expires_at) if expires_at else None
        normalized_reason = reason.strip()
        if not 3 <= len(normalized_reason) <= 300:
            raise ValueError("Причина має містити від 3 до 300 символів.")
        if normalized_expiry is not None and normalized_expiry <= current:
            raise ValueError("Дата завершення VIP має бути в майбутньому.")

        async with self._session_factory() as session, session.begin():
            await self._require_mutable_target(session, target_user_id)
            grant = await session.get(VipGrant, target_user_id)
            if grant is None:
                grant = VipGrant(
                    telegram_user_id=target_user_id,
                    created_at=current,
                )
                session.add(grant)
            grant.is_active = True
            grant.starts_at = current
            grant.expires_at = normalized_expiry
            grant.granted_by_owner_id = actor.telegram_user_id
            grant.grant_reason = normalized_reason
            grant.revoked_at = None
            grant.revoked_by_owner_id = None
            grant.revoke_reason = None
            grant.updated_at = current
            session.add(
                self._audit(
                    actor,
                    "vip.granted",
                    target_user_id,
                    {
                        "mode": "until" if normalized_expiry else "permanent",
                        "expires_at": normalized_expiry.isoformat() if normalized_expiry else None,
                        "reason": normalized_reason,
                    },
                    current,
                )
            )
            await session.flush()
            return self._serialize(grant)

    async def revoke(
        self,
        actor: AdminActor,
        target_user_id: int,
        *,
        reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        actor.require("vip.manage")
        current = _as_utc(now or utc_now())
        normalized_reason = reason.strip()
        if not 3 <= len(normalized_reason) <= 300:
            raise ValueError("Причина має містити від 3 до 300 символів.")

        async with self._session_factory() as session, session.begin():
            await self._require_mutable_target(session, target_user_id)
            grant = await session.get(VipGrant, target_user_id)
            if grant is None or not grant.is_active:
                raise LookupError("Активний VIP не знайдено.")
            grant.is_active = False
            grant.revoked_at = current
            grant.revoked_by_owner_id = actor.telegram_user_id
            grant.revoke_reason = normalized_reason
            grant.updated_at = current
            session.add(
                self._audit(
                    actor,
                    "vip.revoked",
                    target_user_id,
                    {"reason": normalized_reason},
                    current,
                )
            )
            await session.flush()
            return self._serialize(grant)

    @staticmethod
    async def _require_mutable_target(session: AsyncSession, target_user_id: int) -> None:
        user = await session.get(User, target_user_id)
        if user is None:
            raise LookupError("Користувача не знайдено.")
        owner = await session.get(BotOwner, OWNER_KEY)
        if owner is not None and int(owner.telegram_user_id) == target_user_id:
            raise ValueError("Власника ChatPulse не можна змінювати цією дією.")

    @staticmethod
    def _audit(
        actor: AdminActor,
        action: str,
        target_user_id: int,
        metadata: dict[str, Any],
        current: datetime,
    ) -> OwnerAuditLog:
        return OwnerAuditLog(
            owner_telegram_user_id=actor.telegram_user_id,
            action=action,
            target_type="user",
            target_id=str(target_user_id),
            metadata_json=json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            created_at=current,
        )

    @staticmethod
    def _serialize(grant: VipGrant) -> dict[str, Any]:
        return {
            "telegram_user_id": int(grant.telegram_user_id),
            "is_active": bool(grant.is_active),
            "starts_at": _as_utc(grant.starts_at).isoformat(),
            "expires_at": _as_utc(grant.expires_at).isoformat() if grant.expires_at else None,
            "granted_by_owner_id": int(grant.granted_by_owner_id),
            "grant_reason": grant.grant_reason,
            "revoked_at": _as_utc(grant.revoked_at).isoformat() if grant.revoked_at else None,
            "revoke_reason": grant.revoke_reason,
        }
