from .base import *  # noqa: F403
from .base import _as_utc, _display_name, _level_for_xp, _active_vip_clause


class UserStaffMixin:
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
