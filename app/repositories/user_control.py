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


class UserControlRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def resolve_actor(self, telegram_user_id: int) -> AdminActor | None:
        return await resolve_admin_actor(self._session_factory, telegram_user_id)

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

    async def list_users(
        self,
        actor: AdminActor,
        *,
        query: str | None = None,
        vip_filter: VipFilter = "all",
        status_filter: StatusFilter = "all",
        role_filter: str = "all",
        payment_filter: PaymentFilter = "all",
        tag: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort: SortMode = "activity_desc",
        limit: int = 50,
        offset: int = 0,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        actor.require("users.view")
        current = _as_utc(now or utc_now())
        normalized_query = (query or "").strip().casefold()
        normalized_tag = self._normalize_tag(tag) if tag else None

        group_counts = (
            select(
                GroupMember.telegram_user_id.label("user_id"),
                func.count().label("groups_count"),
            )
            .group_by(GroupMember.telegram_user_id)
            .subquery()
        )
        payment_totals = (
            select(
                VipPayment.telegram_user_id.label("user_id"),
                func.count().label("payment_count"),
                func.coalesce(func.sum(VipPayment.stars_amount), 0).label("stars_total"),
                func.max(VipPayment.paid_at).label("last_payment_at"),
            )
            .where(VipPayment.status == "paid")
            .group_by(VipPayment.telegram_user_id)
            .subquery()
        )

        statement = (
            select(
                User,
                VipGrant,
                UserRestriction,
                AdminStaff,
                func.coalesce(group_counts.c.groups_count, 0).label("groups_count"),
                func.coalesce(payment_totals.c.payment_count, 0).label("payment_count"),
                func.coalesce(payment_totals.c.stars_total, 0).label("stars_total"),
                payment_totals.c.last_payment_at,
            )
            .outerjoin(VipGrant, VipGrant.telegram_user_id == User.telegram_id)
            .outerjoin(UserRestriction, UserRestriction.telegram_user_id == User.telegram_id)
            .outerjoin(AdminStaff, AdminStaff.telegram_user_id == User.telegram_id)
            .outerjoin(group_counts, group_counts.c.user_id == User.telegram_id)
            .outerjoin(payment_totals, payment_totals.c.user_id == User.telegram_id)
        )

        if normalized_query:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    func.lower(User.first_name).like(pattern),
                    func.lower(func.coalesce(User.last_name, "")).like(pattern),
                    func.lower(func.coalesce(User.username, "")).like(pattern),
                    cast(User.telegram_id, String).like(pattern),
                )
            )

        active_vip = _active_vip_clause(current)
        if vip_filter == "active":
            statement = statement.where(active_vip)
        elif vip_filter == "inactive":
            statement = statement.where(or_(VipGrant.telegram_user_id.is_(None), ~active_vip))
        elif vip_filter == "expiring":
            statement = statement.where(
                active_vip,
                VipGrant.expires_at.is_not(None),
                VipGrant.expires_at <= current + timedelta(days=7),
            )

        blocked = and_(
            UserRestriction.telegram_user_id.is_not(None),
            UserRestriction.is_blocked.is_(True),
        )
        inactive_before = current - timedelta(days=30)
        if status_filter == "blocked":
            statement = statement.where(blocked)
        elif status_filter == "inactive":
            statement = statement.where(~blocked, User.last_activity_at < inactive_before)
        elif status_filter == "active":
            statement = statement.where(~blocked, User.last_activity_at >= inactive_before)

        if role_filter != "all":
            if role_filter == "owner":
                owner_id = select(BotOwner.telegram_user_id).where(BotOwner.owner_key == OWNER_KEY)
                statement = statement.where(User.telegram_id == owner_id.scalar_subquery())
            elif role_filter in {"admin", "moderator", "support"}:
                statement = statement.where(
                    AdminStaff.role == role_filter,
                    AdminStaff.is_active.is_(True),
                )
            elif role_filter == "none":
                owner_id = select(BotOwner.telegram_user_id).where(BotOwner.owner_key == OWNER_KEY)
                statement = statement.where(
                    AdminStaff.telegram_user_id.is_(None),
                    User.telegram_id != owner_id.scalar_subquery(),
                )

        if payment_filter == "paid":
            statement = statement.where(func.coalesce(payment_totals.c.payment_count, 0) > 0)
        elif payment_filter == "never":
            statement = statement.where(func.coalesce(payment_totals.c.payment_count, 0) == 0)
        if normalized_tag:
            statement = statement.where(
                exists(
                    select(UserAdminTag.telegram_user_id).where(
                        UserAdminTag.telegram_user_id == User.telegram_id,
                        UserAdminTag.tag == normalized_tag,
                    )
                )
            )
        if created_from is not None:
            statement = statement.where(User.created_at >= _as_utc(created_from))
        if created_to is not None:
            statement = statement.where(User.created_at <= _as_utc(created_to))

        sort_map = {
            "activity_desc": User.last_activity_at.desc(),
            "activity_asc": User.last_activity_at.asc(),
            "created_desc": User.created_at.desc(),
            "created_asc": User.created_at.asc(),
            "xp_desc": User.global_xp_total.desc(),
            "xp_asc": User.global_xp_total.asc(),
            "groups_desc": func.coalesce(group_counts.c.groups_count, 0).desc(),
            "groups_asc": func.coalesce(group_counts.c.groups_count, 0).asc(),
            "stars_desc": func.coalesce(payment_totals.c.stars_total, 0).desc(),
            "stars_asc": func.coalesce(payment_totals.c.stars_total, 0).asc(),
            "vip_expiry_asc": VipGrant.expires_at.asc().nulls_last(),
        }
        statement = statement.order_by(sort_map[sort], User.telegram_id.desc())

        async with self._session_factory() as session:
            total = int(
                await session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
                or 0
            )
            rows = (await session.execute(statement.limit(limit).offset(offset))).all()
            owner = await session.get(BotOwner, OWNER_KEY)
            owner_id = int(owner.telegram_user_id) if owner else None
            return {
                "items": [
                    self._serialize_user_row(row, current=current, owner_id=owner_id) for row in rows
                ],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

    async def get_user_detail(
        self,
        actor: AdminActor,
        user_id: int,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        actor.require("users.view")
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session:
            user = await session.get(User, user_id)
            if user is None:
                return None
            owner = await session.get(BotOwner, OWNER_KEY)
            owner_id = int(owner.telegram_user_id) if owner else None
            grant = await session.get(VipGrant, user_id)
            restriction = await session.get(UserRestriction, user_id)
            staff = await session.get(AdminStaff, user_id)
            note = await session.get(UserAdminNote, user_id)
            tags = list(
                (
                    await session.scalars(
                        select(UserAdminTag)
                        .where(UserAdminTag.telegram_user_id == user_id)
                        .order_by(UserAdminTag.tag.asc())
                    )
                ).all()
            )
            groups = (
                await session.execute(
                    select(GroupMember, ChatGroup)
                    .join(ChatGroup, ChatGroup.telegram_chat_id == GroupMember.telegram_chat_id)
                    .where(GroupMember.telegram_user_id == user_id)
                    .order_by(GroupMember.last_seen_at.desc())
                    .limit(100)
                )
            ).all()
            payments = list(
                (
                    await session.scalars(
                        select(VipPayment)
                        .where(VipPayment.telegram_user_id == user_id)
                        .order_by(VipPayment.paid_at.desc())
                        .limit(100)
                    )
                ).all()
            )
            adjustments = list(
                (
                    await session.scalars(
                        select(UserXpAdjustment)
                        .where(UserXpAdjustment.telegram_user_id == user_id)
                        .order_by(UserXpAdjustment.created_at.desc(), UserXpAdjustment.id.desc())
                        .limit(25)
                    )
                ).all()
            )
            deliveries = list(
                (
                    await session.scalars(
                        select(AdminMessageDelivery)
                        .where(AdminMessageDelivery.telegram_user_id == user_id)
                        .order_by(
                            AdminMessageDelivery.created_at.desc(),
                            AdminMessageDelivery.id.desc(),
                        )
                        .limit(25)
                    )
                ).all()
            )
            audit = await self._list_user_audit_in_session(session, actor, user_id, limit=40)

            paid = [row for row in payments if row.status == "paid"]
            stars_total = sum(int(row.stars_amount) for row in paid)
            active_subscription = any(
                row.subscription_expiration_date is not None
                and _as_utc(row.subscription_expiration_date) > current
                and row.status == "paid"
                for row in payments
            )
            active_vip = bool(
                grant
                and grant.is_active
                and (grant.expires_at is None or _as_utc(grant.expires_at) > current)
            )
            return {
                "telegram_id": int(user.telegram_id),
                "display_name": _display_name(user),
                "username": user.username,
                "language_code": user.language_code,
                "created_at": _as_utc(user.created_at).isoformat(),
                "last_activity_at": _as_utc(user.last_activity_at).isoformat(),
                "global_xp_total": int(user.global_xp_total),
                "global_level": int(user.global_level),
                "is_owner": owner_id == user_id,
                "role": "owner" if owner_id == user_id else (staff.role if staff and staff.is_active else None),
                "is_blocked": bool(restriction and restriction.is_blocked),
                "restriction": self._serialize_restriction(restriction) if restriction else None,
                "vip": {
                    "is_active": active_vip,
                    "source": "payment" if paid else ("gifted" if active_vip else None),
                    "starts_at": (
                        _as_utc(grant.starts_at).isoformat() if grant and active_vip else None
                    ),
                    "expires_at": (
                        _as_utc(grant.expires_at).isoformat()
                        if grant and active_vip and grant.expires_at
                        else None
                    ),
                },
                "payment_summary": {
                    "stars_total": stars_total,
                    "payment_count": len(paid),
                    "last_payment_at": (
                        _as_utc(paid[0].paid_at).isoformat() if paid else None
                    ),
                    "active_subscription": active_subscription,
                },
                "note": note.note if note else "",
                "tags": [row.tag for row in tags],
                "groups": [
                    {
                        "telegram_chat_id": int(group.telegram_chat_id),
                        "title": group.title,
                        "username": group.username,
                        "xp_total": int(member.xp_total),
                        "level": int(member.level),
                        "last_seen_at": _as_utc(member.last_seen_at).isoformat(),
                    }
                    for member, group in groups
                ],
                "adjustments": [self._serialize_adjustment(row) for row in adjustments],
                "deliveries": [self._serialize_delivery(row) for row in deliveries],
                "audit": audit,
            }

    async def set_note(self, actor: AdminActor, user_id: int, note: str) -> dict[str, Any]:
        actor.require("users.notes")
        normalized = note.strip()
        if len(normalized) > 4000:
            raise ValueError("Нотатка задовга.")
        current = _as_utc(utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_user(session, user_id)
            record = await session.get(UserAdminNote, user_id)
            if not normalized:
                if record is not None:
                    await session.delete(record)
            elif record is None:
                record = UserAdminNote(
                    telegram_user_id=user_id,
                    note=normalized,
                    updated_by_actor_id=actor.telegram_user_id,
                    updated_at=current,
                )
                session.add(record)
            else:
                record.note = normalized
                record.updated_by_actor_id = actor.telegram_user_id
                record.updated_at = current
            session.add(
                self._audit_entry(
                    actor,
                    action="user.note_updated",
                    target_id=user_id,
                    metadata={"has_note": bool(normalized), "length": len(normalized)},
                    created_at=current,
                )
            )
            return {"telegram_user_id": user_id, "note": normalized, "updated_at": current.isoformat()}

    async def add_tag(self, actor: AdminActor, user_id: int, tag: str) -> dict[str, Any]:
        actor.require("users.notes")
        normalized = self._normalize_tag(tag)
        current = _as_utc(utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_user(session, user_id)
            count = int(
                await session.scalar(
                    select(func.count()).select_from(UserAdminTag).where(
                        UserAdminTag.telegram_user_id == user_id
                    )
                )
                or 0
            )
            existing = await session.get(UserAdminTag, (user_id, normalized))
            if existing is None and count >= 10:
                raise ValueError("Для користувача вже встановлено максимум 10 тегів.")
            if existing is None:
                session.add(
                    UserAdminTag(
                        telegram_user_id=user_id,
                        tag=normalized,
                        created_by_actor_id=actor.telegram_user_id,
                        created_at=current,
                    )
                )
                session.add(
                    self._audit_entry(
                        actor,
                        action="user.tag_added",
                        target_id=user_id,
                        metadata={"tag": normalized},
                        created_at=current,
                    )
                )
            return {"telegram_user_id": user_id, "tag": normalized}

    async def remove_tag(self, actor: AdminActor, user_id: int, tag: str) -> dict[str, Any]:
        actor.require("users.notes")
        normalized = self._normalize_tag(tag)
        current = _as_utc(utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_user(session, user_id)
            result = await session.execute(
                delete(UserAdminTag).where(
                    UserAdminTag.telegram_user_id == user_id,
                    UserAdminTag.tag == normalized,
                )
            )
            if not result.rowcount:
                raise LookupError("Тег не знайдено.")
            session.add(
                self._audit_entry(
                    actor,
                    action="user.tag_removed",
                    target_id=user_id,
                    metadata={"tag": normalized},
                    created_at=current,
                )
            )
            return {"telegram_user_id": user_id, "tag": normalized, "removed": True}

    async def set_role(
        self,
        actor: AdminActor,
        user_id: int,
        role: Literal["admin", "moderator", "support"],
    ) -> dict[str, Any]:
        actor.require("staff.manage")
        current = _as_utc(utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_mutable_target(session, user_id)
            staff = await session.get(AdminStaff, user_id)
            if staff is None:
                staff = AdminStaff(
                    telegram_user_id=user_id,
                    role=role,
                    is_active=True,
                    granted_by_owner_id=actor.telegram_user_id,
                    created_at=current,
                    updated_at=current,
                )
                session.add(staff)
            else:
                staff.role = role
                staff.is_active = True
                staff.granted_by_owner_id = actor.telegram_user_id
                staff.updated_at = current
            session.add(
                self._audit_entry(
                    actor,
                    action="staff.role_set",
                    target_id=user_id,
                    metadata={"role": role},
                    created_at=current,
                )
            )
            return {"telegram_user_id": user_id, "role": role, "is_active": True}

    async def remove_role(self, actor: AdminActor, user_id: int, reason: str) -> dict[str, Any]:
        actor.require("staff.manage")
        normalized_reason = self._reason(reason)
        current = _as_utc(utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_mutable_target(session, user_id)
            staff = await session.get(AdminStaff, user_id)
            if staff is None or not staff.is_active:
                raise LookupError("Активну роль не знайдено.")
            previous_role = staff.role
            staff.is_active = False
            staff.updated_at = current
            session.add(
                self._audit_entry(
                    actor,
                    action="staff.role_removed",
                    target_id=user_id,
                    metadata={"role": previous_role, "reason": normalized_reason},
                    created_at=current,
                )
            )
            return {"telegram_user_id": user_id, "role": None, "is_active": False}

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

    async def list_user_audit(
        self,
        actor: AdminActor,
        user_id: int,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        actor.require("users.view")
        async with self._session_factory() as session:
            return await self._list_user_audit_in_session(session, actor, user_id, limit=limit)

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
