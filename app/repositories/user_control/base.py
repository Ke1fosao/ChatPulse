import json
import math
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import String, and_, cast, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.billing_models import VipPayment
from app.models import (
    BotOwner,
    ChatGroup,
    GroupMember,
    OwnerAuditLog,
    User,
    VipGrant,
    utc_now,
)
from app.repositories.owner import OWNER_KEY
from app.services.admin_access import AdminActor, AdminRole, resolve_admin_actor
from app.user_control_models import (
    AdminMessageDelivery,
    AdminStaff,
    BlockedAccessEvent,
    UserAdminNote,
    UserAdminTag,
    UserRestriction,
    UserXpAdjustment,
)

VipFilter = Literal["all", "active", "inactive", "expiring"]
StatusFilter = Literal["all", "active", "inactive", "blocked"]
PaymentFilter = Literal["all", "paid", "never"]
SortMode = Literal[
    "activity_desc",
    "activity_asc",
    "created_desc",
    "created_asc",
    "xp_desc",
    "xp_asc",
    "groups_desc",
    "groups_asc",
    "stars_desc",
    "stars_asc",
    "vip_expiry_asc",
]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _display_name(user: User) -> str:
    return " ".join(part for part in (user.first_name, user.last_name) if part).strip() or str(
        user.telegram_id
    )


def _level_for_xp(total: int) -> int:
    safe_total = max(0, int(total))
    return max(1, int((1 + math.sqrt(1 + (safe_total / 12.5))) / 2))


def _active_vip_clause(current: datetime):
    return and_(
        VipGrant.is_active.is_(True),
        or_(VipGrant.expires_at.is_(None), VipGrant.expires_at > current),
    )


class UserControlBase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def resolve_actor(self, telegram_user_id: int) -> AdminActor | None:
        return await resolve_admin_actor(self._session_factory, telegram_user_id)

    @staticmethod
    async def _list_user_audit_in_session(
        session: AsyncSession,
        actor: AdminActor,
        user_id: int,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        statement = select(OwnerAuditLog).where(
            OwnerAuditLog.target_type == "user",
            OwnerAuditLog.target_id == str(user_id),
        )
        if not actor.can("audit.view"):
            if not actor.can("audit.view_own"):
                return []
            statement = statement.where(
                OwnerAuditLog.owner_telegram_user_id == actor.telegram_user_id
            )
        rows = list(
            (
                await session.scalars(
                    statement.order_by(
                        OwnerAuditLog.created_at.desc(), OwnerAuditLog.id.desc()
                    ).limit(limit)
                )
            ).all()
        )
        return [UserControlRepository._serialize_audit(row) for row in rows]

    @staticmethod
    async def _require_user(session: AsyncSession, user_id: int) -> User:
        user = await session.get(User, user_id)
        if user is None:
            raise LookupError("Користувача не знайдено.")
        return user

    @staticmethod
    async def _require_mutable_target(session: AsyncSession, user_id: int) -> User:
        user = await UserControlRepository._require_user(session, user_id)
        owner = await session.get(BotOwner, OWNER_KEY)
        if owner is not None and int(owner.telegram_user_id) == user_id:
            raise ValueError("Власника ChatPulse не можна змінювати цією дією.")
        return user

    @staticmethod
    def _reason(value: str) -> str:
        normalized = value.strip()
        if not 3 <= len(normalized) <= 500:
            raise ValueError("Причина має містити від 3 до 500 символів.")
        return normalized

    @staticmethod
    def _normalize_tag(value: str) -> str:
        normalized = " ".join(value.strip().casefold().split())
        if not 1 <= len(normalized) <= 32:
            raise ValueError("Тег має містити від 1 до 32 символів.")
        return normalized

    @staticmethod
    def _audit_entry(
        actor: AdminActor,
        *,
        action: str,
        target_id: int,
        metadata: dict[str, Any],
        created_at: datetime,
    ) -> OwnerAuditLog:
        return OwnerAuditLog(
            owner_telegram_user_id=actor.telegram_user_id,
            action=action,
            target_type="user",
            target_id=str(target_id),
            metadata_json=json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            created_at=created_at,
        )

    @staticmethod
    def _serialize_user_row(row: Any, *, current: datetime, owner_id: int | None) -> dict[str, Any]:
        (
            user,
            grant,
            restriction,
            staff,
            groups_count,
            payment_count,
            stars_total,
            last_payment_at,
        ) = row
        active_vip = bool(
            grant
            and grant.is_active
            and (grant.expires_at is None or _as_utc(grant.expires_at) > current)
        )
        return {
            "telegram_id": int(user.telegram_id),
            "display_name": _display_name(user),
            "username": user.username,
            "global_xp_total": int(user.global_xp_total),
            "global_level": int(user.global_level),
            "groups_count": int(groups_count),
            "is_vip": active_vip,
            "vip_expires_at": (
                _as_utc(grant.expires_at).isoformat()
                if active_vip and grant and grant.expires_at
                else None
            ),
            "is_blocked": bool(restriction and restriction.is_blocked),
            "role": (
                "owner"
                if owner_id == int(user.telegram_id)
                else (staff.role if staff and staff.is_active else None)
            ),
            "payment_count": int(payment_count),
            "stars_total": int(stars_total),
            "last_payment_at": _as_utc(last_payment_at).isoformat() if last_payment_at else None,
            "created_at": _as_utc(user.created_at).isoformat(),
            "last_activity_at": _as_utc(user.last_activity_at).isoformat(),
        }

    @staticmethod
    def _serialize_restriction(restriction: UserRestriction | None) -> dict[str, Any]:
        if restriction is None:
            return {"is_blocked": False, "reason": None, "blocked_at": None}
        return {
            "is_blocked": bool(restriction.is_blocked),
            "reason": restriction.reason,
            "blocked_by_actor_id": restriction.blocked_by_actor_id,
            "blocked_at": (
                _as_utc(restriction.blocked_at).isoformat() if restriction.blocked_at else None
            ),
            "unblocked_by_actor_id": restriction.unblocked_by_actor_id,
            "unblocked_at": (
                _as_utc(restriction.unblocked_at).isoformat() if restriction.unblocked_at else None
            ),
            "unblock_reason": restriction.unblock_reason,
            "updated_at": _as_utc(restriction.updated_at).isoformat(),
        }

    @staticmethod
    def _serialize_adjustment(row: UserXpAdjustment) -> dict[str, Any]:
        return {
            "id": int(row.id),
            "telegram_chat_id": int(row.telegram_chat_id) if row.telegram_chat_id else None,
            "amount": int(row.amount),
            "previous_total": int(row.previous_total),
            "resulting_total": int(row.resulting_total),
            "reason": row.reason,
            "actor_telegram_user_id": int(row.actor_telegram_user_id),
            "created_at": _as_utc(row.created_at).isoformat(),
        }

    @staticmethod
    def _serialize_delivery(row: AdminMessageDelivery) -> dict[str, Any]:
        return {
            "id": int(row.id),
            "telegram_user_id": int(row.telegram_user_id),
            "actor_telegram_user_id": int(row.actor_telegram_user_id),
            "message_text": row.message_text,
            "status": row.status,
            "safe_error": row.safe_error,
            "created_at": _as_utc(row.created_at).isoformat(),
            "sent_at": _as_utc(row.sent_at).isoformat() if row.sent_at else None,
        }

    @staticmethod
    def _serialize_audit(row: OwnerAuditLog) -> dict[str, Any]:
        try:
            metadata = json.loads(row.metadata_json)
        except json.JSONDecodeError:
            metadata = {}
        return {
            "id": int(row.id),
            "actor_telegram_user_id": int(row.owner_telegram_user_id),
            "action": row.action,
            "metadata": metadata,
            "created_at": _as_utc(row.created_at).isoformat(),
        }
