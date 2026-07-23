from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.api.miniapp.schemas import MiniAppPeriod, RankingMetric
from app.repositories.groups_v2 import GroupsV2Repository
from app.services.weekly_reports import send_weekly_report

router = APIRouter(prefix="/api/miniapp/v1", tags=["miniapp-groups-v2"])


class FavoriteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_favorite: bool


def _repository(request: Request) -> GroupsV2Repository:
    return request.app.state.groups_v2_repository


async def _is_current_admin(request: Request, chat_id: int, user_id: int) -> bool:
    return await request.app.state.telegram_access_service.check_admin(chat_id, user_id)


async def _admin_display_flag(request: Request, chat_id: int, user_id: int) -> bool:
    if not request.app.state.settings.webhook_base_url:
        return False
    return await _is_current_admin(request, chat_id, user_id)


async def _require_current_member(request: Request, chat_id: int, user_id: int) -> None:
    if not request.app.state.settings.webhook_base_url:
        return
    if not await request.app.state.telegram_access_service.check_member(chat_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )


async def _require_admin(request: Request, chat_id: int, user_id: int) -> None:
    if not await _is_current_admin(request, chat_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ця дія доступна лише адміністраторам групи.",
        )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Групу не знайдено або доступ відсутній.",
    )


@router.get("/groups-v2")
async def groups_v2(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, list[dict]]:
    items = await _repository(request).list_groups(user.telegram_id)
    for item in items:
        item["is_admin"] = await _admin_display_flag(
            request,
            int(item["telegram_chat_id"]),
            user.telegram_id,
        )
    return {"groups": items}


@router.put("/groups/{chat_id}/favorite")
async def update_favorite(
    chat_id: int,
    payload: FavoriteUpdate,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    try:
        return await _repository(request).set_favorite(
            user.telegram_id,
            chat_id,
            payload.is_favorite,
        )
    except LookupError as error:
        raise _not_found() from error


@router.get("/groups/{chat_id}/overview")
async def group_overview(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    period: Annotated[MiniAppPeriod, Query()] = "week",
) -> dict:
    payload = await _repository(request).get_overview(
        user.telegram_id,
        chat_id,
        period,
    )
    if payload is None:
        raise _not_found()
    await _require_current_member(request, chat_id, user.telegram_id)
    payload["capabilities"] = {
        "is_admin": await _admin_display_flag(request, chat_id, user.telegram_id)
    }
    return payload


@router.get("/groups/{chat_id}/ranking")
async def group_ranking(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    metric: Annotated[RankingMetric, Query()] = "xp",
    period: Annotated[MiniAppPeriod, Query()] = "week",
) -> dict:
    payload = await _repository(request).get_ranking(
        user.telegram_id,
        chat_id,
        metric,
        period,
    )
    if payload is None:
        raise _not_found()
    await _require_current_member(request, chat_id, user.telegram_id)
    return payload


@router.get("/groups/{chat_id}/analytics")
async def group_analytics(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    period: Annotated[MiniAppPeriod, Query()] = "week",
) -> dict:
    payload = await _repository(request).get_analytics(
        user.telegram_id,
        chat_id,
        period,
    )
    if payload is None:
        raise _not_found()
    await _require_current_member(request, chat_id, user.telegram_id)
    return payload


@router.get("/groups/{chat_id}/awards")
async def group_awards(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    period: Annotated[MiniAppPeriod, Query()] = "week",
) -> dict:
    payload = await _repository(request).get_awards(
        user.telegram_id,
        chat_id,
        period,
    )
    if payload is None:
        raise _not_found()
    await _require_current_member(request, chat_id, user.telegram_id)
    return payload


@router.post("/groups/{chat_id}/report-now")
async def send_group_report_now(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, bool]:
    await _require_admin(request, chat_id, user.telegram_id)
    delivered = await send_weekly_report(
        request.app.state.bot,
        request.app.state.repository,
        chat_id,
        retention_service=request.app.state.retention_lifecycle_service,
        mark_sent=False,
    )
    if not delivered:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Не вдалося надіслати звіт у групу.",
        )
    await _repository(request).record_admin_action(
        user.telegram_id,
        chat_id,
        "group.report_sent_manually",
    )
    return {"ok": True}


@router.post("/groups/{chat_id}/analytics/pause")
async def pause_group_analytics(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    await _require_admin(request, chat_id, user.telegram_id)
    try:
        return await _repository(request).set_paused(
            actor_user_id=user.telegram_id,
            chat_id=chat_id,
            is_paused=True,
        )
    except LookupError as error:
        raise _not_found() from error


@router.post("/groups/{chat_id}/analytics/resume")
async def resume_group_analytics(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    await _require_admin(request, chat_id, user.telegram_id)
    try:
        return await _repository(request).set_paused(
            actor_user_id=user.telegram_id,
            chat_id=chat_id,
            is_paused=False,
        )
    except LookupError as error:
        raise _not_found() from error
