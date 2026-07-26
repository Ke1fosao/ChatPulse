from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.miniapp.access import require_current_member
from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.api.miniapp.responses import AchievementEventsResponse, AchievementsResponse, OkResponse
from app.services.achievement_cards import render_achievement_card

router = APIRouter(prefix="/api/miniapp/v1", tags=["miniapp-achievements"])


@router.get("/achievements", response_model=AchievementsResponse)
async def achievements(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    chat_id: Annotated[int | None, Query()] = None,
) -> dict[str, list[dict]]:
    payload = await request.app.state.miniapp_repository.get_achievements(
        user.telegram_id,
        chat_id,
    )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )
    if chat_id is not None:
        await require_current_member(request, chat_id, user.telegram_id)
    return {"achievements": payload}


@router.get("/achievement-events", response_model=AchievementEventsResponse)
async def achievement_events(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    limit: Annotated[int, Query(ge=1, le=25)] = 10,
) -> dict[str, list[dict]]:
    events = await request.app.state.achievement_repository.list_pending_events(
        user.telegram_id,
        limit=limit,
    )
    return {"events": events}


@router.get("/achievement-events/{event_id}/card", response_class=Response)
async def achievement_event_card(
    event_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> Response:
    event = await request.app.state.achievement_repository.get_unlock_event(
        user.telegram_id,
        event_id,
    )
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Досягнення для поширення не знайдено.",
        )
    image = render_achievement_card(
        event,
        display_name=user.display_name,
        username=user.username,
    )
    return Response(
        content=image,
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=chatpulse-achievement-{event_id}.png"},
    )


@router.post("/achievement-events/{event_id}/seen", response_model=OkResponse)
async def mark_achievement_event_seen(
    event_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, bool]:
    if not await request.app.state.achievement_repository.mark_seen(user.telegram_id, event_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подію досягнення не знайдено.",
        )
    return {"ok": True}


@router.post("/achievement-events/{event_id}/shared", response_model=OkResponse)
async def mark_achievement_event_shared(
    event_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, bool]:
    if not await request.app.state.achievement_repository.mark_shared(user.telegram_id, event_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подію досягнення не знайдено.",
        )
    return {"ok": True}
