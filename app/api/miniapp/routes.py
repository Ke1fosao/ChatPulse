from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.api.miniapp.schemas import (
    GroupSettingsUpdate,
    MiniAppPeriod,
    RankingMetric,
    ResetGroupRequest,
)
from app.repositories.achievements import AchievementRepository
from app.repositories.activity import ActivityRepository
from app.repositories.miniapp import MiniAppRepository
from app.repositories.miniapp_gamification import MiniAppGamificationRepository
from app.repositories.owner import OwnerRepository
from app.repositories.owner_panel import OwnerPanelRepository
from app.services.achievement_cards import render_achievement_card
from app.services.levels import build_level_catalog
from app.services.profile_cards import render_profile_card
from app.services.report_cards import render_weekly_report_card
from app.services.telegram_access import TelegramAccessService
from app.services.weekly_payload import build_weekly_payload

router = APIRouter(prefix="/api/miniapp/v1", tags=["miniapp"])


def _repository(request: Request) -> MiniAppRepository:
    return request.app.state.miniapp_repository


def _achievement_repository(request: Request) -> AchievementRepository:
    return request.app.state.achievement_repository


def _activity_repository(request: Request) -> ActivityRepository:
    return request.app.state.repository


def _gamification_repository(request: Request) -> MiniAppGamificationRepository:
    return request.app.state.gamification_repository


def _owner_repository(request: Request) -> OwnerRepository:
    return request.app.state.owner_repository


def _owner_panel_repository(request: Request) -> OwnerPanelRepository:
    return request.app.state.owner_panel_repository


def _access_service(request: Request) -> TelegramAccessService:
    return request.app.state.telegram_access_service


async def _is_current_admin(request: Request, chat_id: int, user_id: int) -> bool:
    return await _access_service(request).check_admin(chat_id, user_id)


async def _admin_display_flag(request: Request, chat_id: int, user_id: int) -> bool:
    if not request.app.state.settings.webhook_base_url:
        return False
    return await _is_current_admin(request, chat_id, user_id)


async def _with_live_admin_flags(
    request: Request,
    user_id: int,
    groups: list[dict],
) -> list[dict]:
    for group in groups:
        group["is_admin"] = await _admin_display_flag(
            request,
            int(group["telegram_chat_id"]),
            user_id,
        )
    return groups


async def _require_current_member(
    request: Request,
    chat_id: int,
    user_id: int,
) -> None:
    if not request.app.state.settings.webhook_base_url:
        return
    if not await _access_service(request).check_member(chat_id, user_id):
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


async def _account_payload(request: Request, user_id: int) -> dict:
    is_owner = await _owner_repository(request).is_owner(user_id)
    account = await _owner_panel_repository(request).get_account_access(
        user_id,
        is_owner=is_owner,
    )
    return account.to_dict()


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
    payload["account"] = await _account_payload(request, user.telegram_id)
    payload["groups"] = await _with_live_admin_flags(
        request,
        user.telegram_id,
        payload["groups"],
    )
    return payload


@router.get("/levels")
async def levels(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    payload = await _repository(request).get_home(user.telegram_id)
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


@router.get("/profile-card")
async def profile_card(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> Response:
    payload = await _repository(request).get_home(user.telegram_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профіль ChatPulse ще не створено.",
        )
    payload["user"]["photo_url"] = user.photo_url
    payload["account"] = await _account_payload(request, user.telegram_id)
    image = render_profile_card(payload)
    return Response(
        content=image,
        media_type="image/png",
        headers={"Content-Disposition": "inline; filename=chatpulse-profile.png"},
    )


@router.get("/groups")
async def groups(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, list[dict]]:
    items = await _repository(request).list_groups(user.telegram_id)
    return {
        "groups": await _with_live_admin_flags(
            request,
            user.telegram_id,
            items,
        )
    }


@router.get("/groups/{chat_id}")
async def group_dashboard(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    period: Annotated[MiniAppPeriod, Query()] = "week",
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
    await _require_current_member(request, chat_id, user.telegram_id)
    payload["capabilities"] = {
        "is_admin": await _admin_display_flag(request, chat_id, user.telegram_id)
    }
    return payload


@router.get("/groups/{chat_id}/weekly-card")
async def weekly_card(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> Response:
    membership = await _repository(request).get_group_dashboard(
        user.telegram_id,
        chat_id,
        "week",
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )
    await _require_current_member(request, chat_id, user.telegram_id)
    payload = await build_weekly_payload(
        _activity_repository(request),
        _gamification_repository(request),
        chat_id,
    )
    image = render_weekly_report_card(payload, str(payload["theme"]))
    return Response(
        content=image,
        media_type="image/png",
        headers={"Content-Disposition": "inline; filename=chatpulse-weekly.png"},
    )


@router.get("/groups/{chat_id}/rankings")
async def rankings(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    metric: Annotated[RankingMetric, Query()] = "xp",
    period: Annotated[MiniAppPeriod, Query()] = "week",
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
    await _require_current_member(request, chat_id, user.telegram_id)
    return payload


@router.get("/achievements")
async def achievements(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    chat_id: Annotated[int | None, Query()] = None,
) -> dict[str, list[dict]]:
    payload = await _repository(request).get_achievements(user.telegram_id, chat_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )
    if chat_id is not None:
        await _require_current_member(request, chat_id, user.telegram_id)
    return {"achievements": payload}


@router.get("/achievement-events")
async def achievement_events(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    limit: Annotated[int, Query(ge=1, le=25)] = 10,
) -> dict[str, list[dict]]:
    events = await _achievement_repository(request).list_pending_events(
        user.telegram_id,
        limit=limit,
    )
    return {"events": events}


@router.get("/achievement-events/{event_id}/card")
async def achievement_event_card(
    event_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> Response:
    event = await _achievement_repository(request).get_unlock_event(
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
        headers={
            "Content-Disposition": (
                f"inline; filename=chatpulse-achievement-{event_id}.png"
            )
        },
    )


@router.post("/achievement-events/{event_id}/seen")
async def mark_achievement_event_seen(
    event_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, bool]:
    if not await _achievement_repository(request).mark_seen(user.telegram_id, event_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подію досягнення не знайдено.",
        )
    return {"ok": True}


@router.post("/achievement-events/{event_id}/shared")
async def mark_achievement_event_shared(
    event_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, bool]:
    if not await _achievement_repository(request).mark_shared(user.telegram_id, event_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подію досягнення не знайдено.",
        )
    return {"ok": True}


@router.patch("/groups/{chat_id}/settings")
async def update_group_settings(
    chat_id: int,
    payload: GroupSettingsUpdate,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    await _require_admin(request, chat_id, user.telegram_id)
    values = payload.model_dump(exclude_none=True)
    report_time = values.pop("report_time", None)
    report_theme = values.pop("report_card_theme", None)
    if report_time is not None:
        hour, minute = (int(piece) for piece in report_time.split(":"))
        await _gamification_repository(request).update_report_time(
            chat_id,
            hour=hour,
            minute=minute,
        )
    if report_theme is not None:
        await _gamification_repository(request).update_report_theme(chat_id, report_theme)

    for field, value in values.items():
        await _activity_repository(request).update_group_setting(chat_id, field, value)

    settings = await _activity_repository(request).get_group_settings(chat_id)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено.",
        )
    extras = await _gamification_repository(request).get_group_extras(chat_id)
    settings.update(extras)
    settings["report_time"] = (
        f"{int(settings['report_hour']):02d}:{int(settings['report_minute']):02d}"
    )
    return settings


@router.post("/groups/{chat_id}/reset")
async def reset_group(
    chat_id: int,
    _payload: ResetGroupRequest,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, bool]:
    await _require_admin(request, chat_id, user.telegram_id)
    await _gamification_repository(request).reset_group_gamification(chat_id)
    await _activity_repository(request).reset_group_stats(chat_id)
    return {"ok": True}
