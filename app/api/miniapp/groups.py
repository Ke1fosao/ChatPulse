from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict

from app.api.miniapp.access import (
    admin_display_flag,
    not_found,
    require_admin,
    require_current_member,
    resolve_group_access,
)
from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.api.miniapp.responses import (
    FavoriteResponse,
    GroupAnalyticsResponse,
    GroupAwardsResponse,
    GroupOverviewResponse,
    GroupRankingResponse,
    GroupsResponse,
    OkResponse,
    PausedResponse,
)
from app.api.miniapp.schemas import MiniAppPeriod, RankingMetric
from app.services.group_status_sync import reconcile_group_bot_status
from app.services.report_cards import render_weekly_report_card
from app.services.weekly_payload import build_weekly_payload
from app.services.weekly_reports import send_weekly_report

router = APIRouter(prefix="/api/miniapp/v1", tags=["miniapp-groups"])


class FavoriteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_favorite: bool


async def _enrich_group_access(
    request: Request,
    user_id: int,
    items: list[dict],
) -> list[dict]:
    if not items:
        return items
    if not request.app.state.settings.webhook_base_url:
        for item in items:
            item["is_admin"] = False
        return items

    access = await resolve_group_access(
        request.app.state.telegram_access_service,
        user_id=user_id,
        chat_ids=[int(item["telegram_chat_id"]) for item in items],
    )
    changed = False
    for item in items:
        chat_id = int(item["telegram_chat_id"])
        snapshot = access[chat_id]
        item["is_admin"] = snapshot.is_admin
        if snapshot.bot_status is not None:
            changed = (
                await reconcile_group_bot_status(
                    request.app.state.database.session_factory,
                    chat_id,
                    snapshot.bot_status,
                )
                or changed
            )

    if changed:
        refreshed = await request.app.state.groups_v2_repository.list_groups(user_id)
        flags = {chat_id: snapshot.is_admin for chat_id, snapshot in access.items()}
        for item in refreshed:
            item["is_admin"] = flags.get(int(item["telegram_chat_id"]), False)
        return refreshed
    return items


@router.get("/groups-v2", response_model=GroupsResponse)
async def groups_v2(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, list[dict]]:
    items = await request.app.state.groups_v2_repository.list_groups(user.telegram_id)
    return {"groups": await _enrich_group_access(request, user.telegram_id, items)}


@router.put("/groups/{chat_id}/favorite", response_model=FavoriteResponse)
async def update_favorite(
    chat_id: int,
    payload: FavoriteUpdate,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    try:
        return await request.app.state.groups_v2_repository.set_favorite(
            user.telegram_id,
            chat_id,
            payload.is_favorite,
        )
    except LookupError as error:
        raise not_found() from error


@router.get("/groups/{chat_id}/overview", response_model=GroupOverviewResponse)
async def group_overview(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    period: Annotated[MiniAppPeriod, Query()] = "week",
) -> dict:
    payload = await request.app.state.groups_v2_repository.get_overview(
        user.telegram_id,
        chat_id,
        period,
    )
    if payload is None:
        raise not_found()
    await require_current_member(request, chat_id, user.telegram_id)
    payload["capabilities"] = {
        "is_admin": await admin_display_flag(request, chat_id, user.telegram_id)
    }
    return payload


@router.get("/groups/{chat_id}/ranking", response_model=GroupRankingResponse)
async def group_ranking(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    metric: Annotated[RankingMetric, Query()] = "xp",
    period: Annotated[MiniAppPeriod, Query()] = "week",
) -> dict:
    payload = await request.app.state.groups_v2_repository.get_ranking(
        user.telegram_id,
        chat_id,
        metric,
        period,
    )
    if payload is None:
        raise not_found()
    await require_current_member(request, chat_id, user.telegram_id)
    return payload


@router.get("/groups/{chat_id}/analytics", response_model=GroupAnalyticsResponse)
async def group_analytics(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    period: Annotated[MiniAppPeriod, Query()] = "week",
) -> dict:
    payload = await request.app.state.groups_v2_repository.get_analytics(
        user.telegram_id,
        chat_id,
        period,
    )
    if payload is None:
        raise not_found()
    await require_current_member(request, chat_id, user.telegram_id)
    return payload


@router.get("/groups/{chat_id}/awards", response_model=GroupAwardsResponse)
async def group_awards(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    period: Annotated[MiniAppPeriod, Query()] = "week",
) -> dict:
    payload = await request.app.state.groups_v2_repository.get_awards(
        user.telegram_id,
        chat_id,
        period,
    )
    if payload is None:
        raise not_found()
    await require_current_member(request, chat_id, user.telegram_id)
    return payload


@router.get("/groups/{chat_id}/weekly-card", response_class=Response)
async def weekly_card(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> Response:
    membership = await request.app.state.miniapp_repository.get_group_dashboard(
        user.telegram_id,
        chat_id,
        "week",
    )
    if membership is None:
        raise not_found()
    await require_current_member(request, chat_id, user.telegram_id)
    payload = await build_weekly_payload(
        request.app.state.repository,
        request.app.state.gamification_repository,
        chat_id,
    )
    image = render_weekly_report_card(payload, str(payload["theme"]))
    return Response(
        content=image,
        media_type="image/png",
        headers={"Content-Disposition": "inline; filename=chatpulse-weekly.png"},
    )


@router.post("/groups/{chat_id}/report-now", response_model=OkResponse)
async def send_group_report_now(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, bool]:
    await require_admin(request, chat_id, user.telegram_id)
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
    await request.app.state.groups_v2_repository.record_admin_action(
        user.telegram_id,
        chat_id,
        "group.report_sent_manually",
    )
    return {"ok": True}


@router.post("/groups/{chat_id}/analytics/pause", response_model=PausedResponse)
async def pause_group_analytics(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    await require_admin(request, chat_id, user.telegram_id)
    try:
        return await request.app.state.groups_v2_repository.set_paused(
            actor_user_id=user.telegram_id,
            chat_id=chat_id,
            is_paused=True,
        )
    except LookupError as error:
        raise not_found() from error


@router.post("/groups/{chat_id}/analytics/resume", response_model=PausedResponse)
async def resume_group_analytics(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    await require_admin(request, chat_id, user.telegram_id)
    try:
        return await request.app.state.groups_v2_repository.set_paused(
            actor_user_id=user.telegram_id,
            chat_id=chat_id,
            is_paused=False,
        )
    except LookupError as error:
        raise not_found() from error
