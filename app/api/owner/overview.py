from .common import *  # noqa: F403
from .common import (
    _raise_repository_error,
    _repository,
    _send_user_message,
    _user_repository,
    _vip_service,
)

router = APIRouter()


@router.get("/overview")
async def owner_overview(
    request: Request,
    _user: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    return await _repository(request).get_overview()
