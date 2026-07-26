from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.miniapp.access import account_payload, resolve_group_access
from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.api.miniapp.responses import HomeResponse

router = APIRouter(prefix="/api/miniapp/v1", tags=["miniapp-home"])


@router.get("/home", response_model=HomeResponse)
async def home(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    payload = await request.app.state.miniapp_repository.get_home(user.telegram_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профіль ChatPulse ще не створено. Напишіть /start боту.",
        )
    payload["user"]["photo_url"] = user.photo_url
    payload["account"] = await account_payload(request, user.telegram_id)
    groups = payload["groups"]
    if not groups or not request.app.state.settings.webhook_base_url:
        for group in groups:
            group["is_admin"] = False
    else:
        access = await resolve_group_access(
            request.app.state.telegram_access_service,
            user_id=user.telegram_id,
            chat_ids=[int(group["telegram_chat_id"]) for group in groups],
        )
        for group in groups:
            group["is_admin"] = access[int(group["telegram_chat_id"])].is_admin
    return payload
