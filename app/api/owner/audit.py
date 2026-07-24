# ruff: noqa: F401, F403, F405, F821, I001
from .common import *  # noqa: F403
from .common import (
    _raise_repository_error,
    _repository,
    _send_user_message,
    _user_repository,
    _vip_service,
)

router = APIRouter()


@router.get("/audit")
async def owner_audit(
    request: Request,
    _user: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, list[dict]]:
    return {"items": await _repository(request).list_audit(limit=limit)}
