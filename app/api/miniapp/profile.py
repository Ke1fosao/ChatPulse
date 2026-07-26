from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.api.miniapp.responses import LevelsResponse
from app.services.levels import build_level_catalog

router = APIRouter(prefix="/api/miniapp/v1", tags=["miniapp-profile"])


@router.get("/levels", response_model=LevelsResponse)
async def levels(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    payload = await request.app.state.miniapp_repository.get_home(user.telegram_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профіль ChatPulse ще не створено.",
        )
    progress = payload["global_progress"]
    return build_level_catalog(
        current_level=int(progress["level"]),
        xp_total=int(progress["xp_total"]),
    )
