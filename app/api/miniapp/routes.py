from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.api.miniapp.schemas import MiniAppPeriod, RankingMetric
from app.repositories.miniapp import MiniAppRepository

router = APIRouter(prefix="/api/miniapp/v1", tags=["miniapp"])


def _repository(request: Request) -> MiniAppRepository:
    return request.app.state.miniapp_repository


@router.get("/home")
async def home(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    payload = await _repository(request).get_home(user.telegram_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профіль ChatPulse ще не створено. Напишіть /start боту.",
        )
    payload["user"]["photo_url"] = user.photo_url
    return payload


@router.get("/groups")
async def groups(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, list[dict]]:
    return {"groups": await _repository(request).list_groups(user.telegram_id)}


@router.get("/groups/{chat_id}")
async def group_dashboard(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    period: MiniAppPeriod = Query(default="week"),
) -> dict:
    payload = await _repository(request).get_group_dashboard(
        user.telegram_id,
        chat_id,
        period,
    )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )
    return payload


@router.get("/groups/{chat_id}/rankings")
async def rankings(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    metric: RankingMetric = Query(default="xp"),
    period: MiniAppPeriod = Query(default="week"),
) -> dict:
    payload = await _repository(request).get_rankings(
        user.telegram_id,
        chat_id,
        metric,
        period,
    )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )
    return payload


@router.get("/achievements")
async def achievements(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    chat_id: int | None = Query(default=None),
) -> dict[str, list[dict]]:
    payload = await _repository(request).get_achievements(user.telegram_id, chat_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )
    return {"achievements": payload}
