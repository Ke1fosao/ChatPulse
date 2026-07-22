from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.repositories.owner import OwnerRepository


async def get_owner_user(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> TelegramMiniAppUser:
    repository: OwnerRepository = request.app.state.owner_repository
    if not await repository.is_owner(user.telegram_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner Panel доступна лише власнику ChatPulse.",
        )
    return user
