from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user

router = APIRouter(prefix="/api/miniapp/v1", tags=["featured-achievements"])


class FeaturedAchievementUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codes: list[str] = Field(default_factory=list, max_length=3)


@router.get("/featured-achievements")
async def featured_achievements(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    items = await request.app.state.featured_achievement_repository.list_featured(
        user.telegram_id
    )
    return {"items": items}


@router.put("/featured-achievements")
async def update_featured_achievements(
    payload: FeaturedAchievementUpdate,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    is_owner = await request.app.state.owner_repository.is_owner(user.telegram_id)
    access = await request.app.state.owner_panel_repository.get_account_access(
        user.telegram_id,
        is_owner=is_owner,
    )
    if not (access.is_owner or access.is_vip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Закріплення досягнень доступне у ChatPulse VIP.",
        )
    try:
        items = await request.app.state.featured_achievement_repository.set_featured_codes(
            user.telegram_id,
            payload.codes,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return {"items": items}
