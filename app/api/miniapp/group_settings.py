from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.miniapp.access import require_admin
from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.api.miniapp.responses import GroupSettingsResponse, OkResponse
from app.api.miniapp.schemas import GroupSettingsUpdate, ResetGroupRequest

router = APIRouter(prefix="/api/miniapp/v1", tags=["miniapp-group-settings"])


@router.patch("/groups/{chat_id}/settings", response_model=GroupSettingsResponse)
async def update_group_settings(
    chat_id: int,
    payload: GroupSettingsUpdate,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    await require_admin(request, chat_id, user.telegram_id)
    try:
        return await request.app.state.group_settings_service.update_settings(
            actor_user_id=user.telegram_id,
            chat_id=chat_id,
            values=payload.model_dump(exclude_none=True),
        )
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено.",
        ) from error


@router.post("/groups/{chat_id}/reset", response_model=OkResponse)
async def reset_group(
    chat_id: int,
    _payload: ResetGroupRequest,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, bool]:
    await require_admin(request, chat_id, user.telegram_id)
    try:
        await request.app.state.group_settings_service.reset_group(
            actor_user_id=user.telegram_id,
            chat_id=chat_id,
        )
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено.",
        ) from error
    return {"ok": True}
