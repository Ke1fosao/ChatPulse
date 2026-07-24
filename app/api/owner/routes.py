from fastapi import APIRouter

from app.api.owner.session import router as session_router
from app.api.owner.overview import router as overview_router
from app.api.owner.users import router as users_router
from app.api.owner.groups import router as groups_router
from app.api.owner.audit import router as audit_router

router = APIRouter(prefix="/api/owner/v1", tags=["owner"])

router.include_router(session_router)
router.include_router(overview_router)
router.include_router(users_router)
router.include_router(groups_router)
router.include_router(audit_router)

from app.api.owner.session import owner_session  # noqa: E402,F401
from app.api.owner.overview import owner_overview  # noqa: E402,F401
from app.api.owner.users import owner_users, owner_users_bulk, owner_user_detail, grant_vip, revoke_vip, block_user, unblock_user, update_user_note, add_user_tag, remove_user_tag, adjust_user_xp, update_user_role, remove_user_role, message_user, user_audit  # noqa: E402,F401
from app.api.owner.groups import owner_groups, update_owner_group  # noqa: E402,F401
from app.api.owner.audit import owner_audit  # noqa: E402,F401
