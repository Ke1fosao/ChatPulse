from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import BotOwner
from app.repositories.owner import OWNER_KEY
from app.user_control_models import AdminStaff

AdminRole = Literal["owner", "admin", "moderator", "support"]

OWNER_PERMISSIONS = frozenset(
    {
        "users.view",
        "audit.view",
        "audit.view_own",
        "vip.manage",
        "xp.manage",
        "users.block",
        "users.notes",
        "users.message",
        "bulk.vip",
        "bulk.block",
        "bulk.tag_message",
        "staff.manage",
    }
)

ROLE_PERMISSIONS: dict[AdminRole, frozenset[str]] = {
    "owner": OWNER_PERMISSIONS,
    "admin": frozenset(permission for permission in OWNER_PERMISSIONS if permission != "staff.manage"),
    "moderator": frozenset(
        {
            "users.view",
            "audit.view_own",
            "users.block",
            "users.notes",
            "users.message",
            "bulk.tag_message",
        }
    ),
    "support": frozenset(
        {
            "users.view",
            "users.notes",
            "users.message",
        }
    ),
}


@dataclass(frozen=True, slots=True)
class AdminActor:
    telegram_user_id: int
    role: AdminRole
    permissions: frozenset[str]

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"

    def can(self, permission: str) -> bool:
        return permission in self.permissions

    def require(self, permission: str) -> None:
        if not self.can(permission):
            raise PermissionError(f"missing permission: {permission}")

    def to_dict(self) -> dict[str, object]:
        return {
            "telegram_user_id": self.telegram_user_id,
            "role": self.role,
            "permissions": sorted(self.permissions),
            "is_owner": self.is_owner,
        }


async def resolve_admin_actor(
    session_factory: async_sessionmaker[AsyncSession],
    telegram_user_id: int,
) -> AdminActor | None:
    async with session_factory() as session:
        owner = await session.get(BotOwner, OWNER_KEY)
        if owner is not None and int(owner.telegram_user_id) == telegram_user_id:
            return AdminActor(
                telegram_user_id=telegram_user_id,
                role="owner",
                permissions=ROLE_PERMISSIONS["owner"],
            )

        staff = await session.get(AdminStaff, telegram_user_id)
        if staff is None or not staff.is_active:
            return None
        role = staff.role
        if role not in {"admin", "moderator", "support"}:
            return None
        typed_role: AdminRole = role  # type: ignore[assignment]
        return AdminActor(
            telegram_user_id=telegram_user_id,
            role=typed_role,
            permissions=ROLE_PERMISSIONS[typed_role],
        )
