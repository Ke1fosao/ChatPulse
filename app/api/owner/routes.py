from fastapi import APIRouter

from app.api.owner.audit import owner_audit, router as audit_router
from app.api.owner.common import _vip_service
from app.api.owner.groups import owner_groups, router as groups_router, update_owner_group
from app.api.owner.overview import owner_overview, router as overview_router
from app.api.owner.session import owner_session, router as session_router
from app.api.owner.users import (
    add_user_tag,
    adjust_user_xp,
    block_user,
    grant_vip,
    message_user,
    owner_user_detail,
    owner_users,
    owner_users_bulk,
    remove_user_role,
    remove_user_tag,
    revoke_vip,
    router as users_router,
    unblock_user,
    update_user_note,
    update_user_role,
    user_audit,
)

router = APIRouter(prefix="/api/owner/v1", tags=["owner"])

router.include_router(session_router)
router.include_router(overview_router)
router.include_router(users_router)
router.include_router(groups_router)
router.include_router(audit_router)

__all__ = [
    "_vip_service",
    "add_user_tag",
    "adjust_user_xp",
    "block_user",
    "grant_vip",
    "message_user",
    "owner_audit",
    "owner_group",
    "owner_groups",
    "owner_overview",
    "owner_session",
    "owner_user_detail",
    "owner_users",
    "owner_users_bulk",
    "remove_user_role",
    "remove_user_tag",
    "revoke_vip",
    "router",
    "unblock_user",
    "update_owner_group",
    "update_user_note",
    "update_user_role",
    "user_audit",
]
