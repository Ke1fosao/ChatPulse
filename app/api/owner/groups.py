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


@router.get("/groups")
async def owner_groups(
    request: Request,
    _user: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
    q: Annotated[str | None, Query(max_length=128)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return await _repository(request).list_groups(query=q, limit=limit, offset=offset)


@router.patch("/groups/{chat_id}")
async def update_owner_group(
    chat_id: int,
    payload: OwnerGroupUpdate,
    request: Request,
    owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    try:
        return await _repository(request).update_group(
            owner_user_id=owner.telegram_id,
            chat_id=chat_id,
            values=payload.model_dump(exclude={"confirmation"}, exclude_none=True),
        )
    except Exception as error:
        _raise_repository_error(error)
        raise
