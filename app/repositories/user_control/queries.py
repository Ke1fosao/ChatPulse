from .base import *  # noqa: F403
from .base import _as_utc, _display_name, _level_for_xp, _active_vip_clause


class UserQueriesMixin:
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
                await session.scalar(
                    select(func.count()).select_from(statement.order_by(None).subquery())
                )
                or 0
            )
            rows = (await session.execute(statement.limit(limit).offset(offset))).all()
            owner = await session.get(BotOwner, OWNER_KEY)
            owner_id = int(owner.telegram_user_id) if owner else None
            return {
                "items": [
                    self._serialize_user_row(row, current=current, owner_id=owner_id)
                    for row in rows
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
                "role": "owner"
                if owner_id == user_id
                else (staff.role if staff and staff.is_active else None),
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
                    "last_payment_at": (_as_utc(paid[0].paid_at).isoformat() if paid else None),
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
