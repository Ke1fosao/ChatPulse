# ruff: noqa: F401, F403, F405, F821, I001
from .base import *  # noqa: F403
from .base import _as_utc, _display_name, _level_for_xp, _active_vip_clause


class UserAuditMixin:
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
