import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    BotOwner,
    ChatGroup,
    DailyActivity,
    GroupMember,
    OwnerAuditLog,
    User,
    VipGrant,
    utc_now,
)
from app.repositories.owner import OWNER_KEY
from app.services.entitlements import AccountAccess, build_account_access

VipFilter = Literal["all", "active", "inactive"]
ALLOWED_GROUP_FIELDS = {
    "is_active",
    "is_paused",
    "weekly_reports_enabled",
    "report_card_theme",
}
ALLOWED_REPORT_THEMES = {"dark_pulse", "telegram_wave", "clean_light"}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class OwnerPanelRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_account_access(
        self,
        user_id: int,
        *,
        is_owner: bool,
        now: datetime | None = None,
    ) -> AccountAccess:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session:
            grant = await session.get(VipGrant, user_id)
            return build_account_access(
                is_owner=is_owner,
                vip_is_active=bool(grant and grant.is_active),
                vip_expires_at=_as_utc(grant.expires_at) if grant and grant.expires_at else None,
                now=current,
            )

    async def is_active_vip(self, user_id: int, *, now: datetime | None = None) -> bool:
        access = await self.get_account_access(user_id, is_owner=False, now=now)
        return access.is_vip

    async def grant_vip(
        self,
        *,
        owner_user_id: int,
        target_user_id: int,
        expires_at: datetime | None,
        reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        normalized_expiry = _as_utc(expires_at) if expires_at else None
        if normalized_expiry is not None and normalized_expiry <= current:
            raise ValueError("VIP expiry must be in the future")

        async with self._session_factory() as session, session.begin():
            owner = await self._require_owner(session, owner_user_id)
            if int(owner.telegram_user_id) == target_user_id:
                raise ValueError("owner cannot be targeted by VIP mutations")
            target = await session.get(User, target_user_id)
            if target is None:
                raise LookupError("User is not registered")

            grant = await session.get(VipGrant, target_user_id)
            if grant is None:
                grant = VipGrant(
                    telegram_user_id=target_user_id,
                    is_active=True,
                    starts_at=current,
                    expires_at=normalized_expiry,
                    granted_by_owner_id=owner_user_id,
                    grant_reason=reason,
                    created_at=current,
                    updated_at=current,
                )
                session.add(grant)
            else:
                grant.is_active = True
                grant.starts_at = current
                grant.expires_at = normalized_expiry
                grant.granted_by_owner_id = owner_user_id
                grant.grant_reason = reason
                grant.revoked_at = None
                grant.revoked_by_owner_id = None
                grant.revoke_reason = None
                grant.updated_at = current

            session.add(
                self._audit_entry(
                    owner_user_id,
                    action="vip.granted",
                    target_type="user",
                    target_id=str(target_user_id),
                    metadata={
                        "mode": "until" if normalized_expiry else "permanent",
                        "expires_at": normalized_expiry.isoformat() if normalized_expiry else None,
                        "reason": reason,
                    },
                    created_at=current,
                )
            )
            await session.flush()
            return self._serialize_grant(grant)

    async def revoke_vip(
        self,
        *,
        owner_user_id: int,
        target_user_id: int,
        reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            owner = await self._require_owner(session, owner_user_id)
            if int(owner.telegram_user_id) == target_user_id:
                raise ValueError("owner cannot be targeted by VIP mutations")
            grant = await session.get(VipGrant, target_user_id)
            if grant is None:
                raise LookupError("VIP grant does not exist")

            grant.is_active = False
            grant.revoked_at = current
            grant.revoked_by_owner_id = owner_user_id
            grant.revoke_reason = reason
            grant.updated_at = current
            session.add(
                self._audit_entry(
                    owner_user_id,
                    action="vip.revoked",
                    target_type="user",
                    target_id=str(target_user_id),
                    metadata={"reason": reason},
                    created_at=current,
                )
            )
            await session.flush()
            return self._serialize_grant(grant)

    async def get_overview(self, *, now: datetime | None = None) -> dict[str, int]:
        current = _as_utc(now or utc_now())
        seven_days_ago = current.date() - timedelta(days=6)
        async with self._session_factory() as session:
            users_total = int(await session.scalar(select(func.count()).select_from(User)) or 0)
            groups_total = int(await session.scalar(select(func.count()).select_from(ChatGroup)) or 0)
            active_groups = int(
                await session.scalar(
                    select(func.count()).select_from(ChatGroup).where(ChatGroup.is_active.is_(True))
                )
                or 0
            )
            vip_total = int(
                await session.scalar(
                    select(func.count())
                    .select_from(VipGrant)
                    .where(
                        VipGrant.is_active.is_(True),
                        or_(VipGrant.expires_at.is_(None), VipGrant.expires_at > current),
                    )
                )
                or 0
            )
            messages_7d = int(
                await session.scalar(
                    select(func.coalesce(func.sum(DailyActivity.messages_count), 0)).where(
                        DailyActivity.activity_date >= seven_days_ago
                    )
                )
                or 0
            )
            return {
                "users_total": users_total,
                "groups_total": groups_total,
                "active_groups": active_groups,
                "vip_total": vip_total,
                "messages_7d": messages_7d,
            }

    async def list_users(
        self,
        *,
        query: str | None,
        vip_filter: VipFilter,
        limit: int,
        offset: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        normalized_query = (query or "").strip().casefold()
        async with self._session_factory() as session:
            users_query = select(User).order_by(User.last_activity_at.desc(), User.telegram_id.desc())
            if normalized_query:
                pattern = f"%{normalized_query}%"
                users_query = users_query.where(
                    or_(
                        func.lower(User.first_name).like(pattern),
                        func.lower(func.coalesce(User.last_name, "")).like(pattern),
                        func.lower(func.coalesce(User.username, "")).like(pattern),
                        func.cast(User.telegram_id, type_=User.telegram_id.type).like(pattern),
                    )
                )
            users = list((await session.scalars(users_query)).all())

            items: list[dict[str, Any]] = []
            for user in users:
                grant = await session.get(VipGrant, int(user.telegram_id))
                active_vip = bool(
                    grant
                    and grant.is_active
                    and (grant.expires_at is None or _as_utc(grant.expires_at) > current)
                )
                if vip_filter == "active" and not active_vip:
                    continue
                if vip_filter == "inactive" and active_vip:
                    continue
                groups_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(GroupMember)
                        .where(GroupMember.telegram_user_id == user.telegram_id)
                    )
                    or 0
                )
                display_name = " ".join(
                    part for part in (user.first_name, user.last_name) if part
                ).strip()
                items.append(
                    {
                        "telegram_id": int(user.telegram_id),
                        "display_name": display_name or str(user.telegram_id),
                        "username": user.username,
                        "global_xp_total": int(user.global_xp_total),
                        "groups_count": groups_count,
                        "is_vip": active_vip,
                        "vip_expires_at": (
                            _as_utc(grant.expires_at).isoformat()
                            if active_vip and grant and grant.expires_at
                            else None
                        ),
                        "last_activity_at": _as_utc(user.last_activity_at).isoformat(),
                    }
                )

            total = len(items)
            return {"items": items[offset : offset + limit], "total": total}

    async def get_user(self, user_id: int, *, now: datetime | None = None) -> dict[str, Any] | None:
        result = await self.list_users(
            query=str(user_id),
            vip_filter="all",
            limit=100,
            offset=0,
            now=now,
        )
        return next((item for item in result["items"] if item["telegram_id"] == user_id), None)

    async def list_groups(
        self,
        *,
        query: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        normalized_query = (query or "").strip().casefold()
        async with self._session_factory() as session:
            groups_query = select(ChatGroup).order_by(ChatGroup.updated_at.desc())
            if normalized_query:
                pattern = f"%{normalized_query}%"
                groups_query = groups_query.where(
                    or_(
                        func.lower(ChatGroup.title).like(pattern),
                        func.lower(func.coalesce(ChatGroup.username, "")).like(pattern),
                    )
                )
            groups = list((await session.scalars(groups_query)).all())
            items: list[dict[str, Any]] = []
            for group in groups:
                members_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(GroupMember)
                        .where(GroupMember.telegram_chat_id == group.telegram_chat_id)
                    )
                    or 0
                )
                items.append(
                    {
                        "telegram_chat_id": int(group.telegram_chat_id),
                        "title": group.title,
                        "username": group.username,
                        "is_active": bool(group.is_active),
                        "is_paused": bool(group.is_paused),
                        "weekly_reports_enabled": bool(group.weekly_reports_enabled),
                        "report_card_theme": group.report_card_theme,
                        "members_count": members_count,
                        "updated_at": _as_utc(group.updated_at).isoformat(),
                    }
                )
            total = len(items)
            return {"items": items[offset : offset + limit], "total": total}

    async def update_group(
        self,
        *,
        owner_user_id: int,
        chat_id: int,
        values: dict[str, Any],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _as_utc(now or utc_now())
        unknown = set(values) - ALLOWED_GROUP_FIELDS
        if unknown:
            raise ValueError(f"Unsupported group fields: {', '.join(sorted(unknown))}")
        theme = values.get("report_card_theme")
        if theme is not None and theme not in ALLOWED_REPORT_THEMES:
            raise ValueError("Unsupported report theme")

        async with self._session_factory() as session, session.begin():
            await self._require_owner(session, owner_user_id)
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                raise LookupError("Group is not registered")
            for field, value in values.items():
                setattr(group, field, value)
            group.updated_at = current
            session.add(
                self._audit_entry(
                    owner_user_id,
                    action="group.updated",
                    target_type="group",
                    target_id=str(chat_id),
                    metadata={"changes": values},
                    created_at=current,
                )
            )
            await session.flush()
            return {
                "telegram_chat_id": int(group.telegram_chat_id),
                "title": group.title,
                "is_active": bool(group.is_active),
                "is_paused": bool(group.is_paused),
                "weekly_reports_enabled": bool(group.weekly_reports_enabled),
                "report_card_theme": group.report_card_theme,
            }

    async def list_audit(self, *, limit: int = 50) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            rows = list(
                (
                    await session.scalars(
                        select(OwnerAuditLog)
                        .order_by(OwnerAuditLog.created_at.desc(), OwnerAuditLog.id.desc())
                        .limit(limit)
                    )
                ).all()
            )
            return [self._serialize_audit(row) for row in rows]

    @staticmethod
    async def _require_owner(session: AsyncSession, owner_user_id: int) -> BotOwner:
        owner = await session.get(BotOwner, OWNER_KEY)
        if owner is None or int(owner.telegram_user_id) != owner_user_id:
            raise PermissionError("owner authorization failed")
        return owner

    @staticmethod
    def _audit_entry(
        owner_user_id: int,
        *,
        action: str,
        target_type: str,
        target_id: str,
        metadata: dict[str, Any],
        created_at: datetime,
    ) -> OwnerAuditLog:
        return OwnerAuditLog(
            owner_telegram_user_id=owner_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            created_at=created_at,
        )

    @staticmethod
    def _serialize_grant(grant: VipGrant) -> dict[str, Any]:
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

    @staticmethod
    def _serialize_audit(row: OwnerAuditLog) -> dict[str, Any]:
        try:
            metadata = json.loads(row.metadata_json)
        except json.JSONDecodeError:
            metadata = {}
        return {
            "id": int(row.id),
            "owner_telegram_user_id": int(row.owner_telegram_user_id),
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "metadata": metadata,
            "created_at": _as_utc(row.created_at).isoformat(),
        }
