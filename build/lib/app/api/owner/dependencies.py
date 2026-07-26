from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.repositories.owner import OwnerRepository
from app.repositories.user_control import UserControlRepository
from app.services.admin_access import AdminActor


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


async def get_admin_actor(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> AdminActor:
    repository: UserControlRepository = request.app.state.user_control_repository
    actor = await repository.resolve_actor(user.telegram_id)
    if actor is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ADMIN_ACCESS_DENIED",
                "message": "Панель керування доступна лише команді ChatPulse.",
            },
        )
    return actor


def require_permission(actor: AdminActor, permission: str) -> None:
    if not actor.can(permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PERMISSION_DENIED",
                "message": "Недостатньо прав для цієї дії.",
                "permission": permission,
            },
        )
