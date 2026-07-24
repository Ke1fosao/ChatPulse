from .common import *  # noqa: F403
from .common import (
    _raise_repository_error,
    _repository,
    _send_user_message,
    _user_repository,
    _vip_service,
)

router = APIRouter()


@router.get("/session")
async def owner_session(
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    account = build_account_access(
        is_owner=actor.is_owner,
        vip_is_active=False,
        vip_expires_at=None,
    )
    return {
        "owner": {
            "telegram_id": user.telegram_id,
            "display_name": user.display_name,
            "username": user.username,
            "photo_url": user.photo_url,
        },
        "actor": actor.to_dict(),
        "account": account.to_dict(),
    }
