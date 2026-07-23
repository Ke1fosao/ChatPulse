from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.repositories.vip_product_events import ALLOWED_EVENT_TYPES
from app.services.premium_policy import PREMIUM_REPORT_THEMES

router = APIRouter(prefix="/api/miniapp/v1/premium", tags=["premium-context"])
PremiumPeriod = Literal["quarter", "half_year", "year"]
PremiumTheme = Literal["telegram_wave", "clean_light", "aurora_gold"]


class VipProductEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: Literal[
        "vip_viewed",
        "vip_plan_selected",
        "vip_invoice_opened",
        "vip_payment_completed",
        "vip_payment_canceled",
        "vip_feature_previewed",
        "vip_feature_unlocked",
    ]
    source: str = Field(min_length=1, max_length=96)
    feature_key: str | None = Field(default=None, max_length=96)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PremiumThemeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: PremiumTheme


async def _account(request: Request, user_id: int):
    is_owner = await request.app.state.owner_repository.is_owner(user_id)
    return await request.app.state.owner_panel_repository.get_account_access(
        user_id,
        is_owner=is_owner,
    )


def _has(account, entitlement: str) -> bool:
    return bool(
        account.is_owner
        or "premium.all" in account.entitlements
        or entitlement in account.entitlements
    )


async def _require_admin(request: Request, chat_id: int, user_id: int) -> None:
    if not await request.app.state.telegram_access_service.check_admin(chat_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ця дія доступна лише адміністраторам групи.",
        )


async def _require_member(request: Request, chat_id: int, user_id: int) -> None:
    if not request.app.state.settings.webhook_base_url:
        return
    if not await request.app.state.telegram_access_service.check_member(chat_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )


@router.get("/context")
async def premium_context(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    account = await _account(request, user.telegram_id)
    billing = await request.app.state.billing_repository.get_status(user.telegram_id)
    return {
        "account": account.to_dict(),
        "trial_available": bool(billing["trial_available"] and not account.is_owner),
        "active_subscription": billing["active_subscription"],
    }


@router.get("/groups/{chat_id}/analytics")
async def premium_group_analytics(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    period: Annotated[PremiumPeriod, Query()] = "quarter",
    compare: Annotated[PremiumPeriod | None, Query()] = None,
) -> dict:
    account = await _account(request, user.telegram_id)
    if not _has(account, "analytics.extended_history"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Розширена аналітика доступна у ChatPulse VIP.",
        )
    payload = await request.app.state.miniapp_repository.get_premium_analytics(
        user.telegram_id,
        chat_id,
        period,
        compare=compare,
    )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )
    await _require_member(request, chat_id, user.telegram_id)
    return payload


@router.get("/groups/{chat_id}/ranking-plans")
async def ranking_account_plans(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, dict[str, str]]:
    ranking = await request.app.state.miniapp_repository.get_rankings(
        user.telegram_id,
        chat_id,
        "xp",
        "week",
    )
    if ranking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )
    await _require_member(request, chat_id, user.telegram_id)
    plans: dict[str, str] = {}
    for row in ranking["rows"]:
        member_id = int(row["telegram_user_id"])
        plans[str(member_id)] = (await _account(request, member_id)).plan
    return {"plans": plans}


@router.put("/groups/{chat_id}/report-theme")
async def premium_report_theme(
    chat_id: int,
    payload: PremiumThemeRequest,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, str]:
    account = await _account(request, user.telegram_id)
    if not _has(account, "reports.premium_themes"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium-теми доступні у ChatPulse VIP.",
        )
    await _require_admin(request, chat_id, user.telegram_id)
    if payload.theme not in PREMIUM_REPORT_THEMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported premium theme",
        )
    await request.app.state.gamification_repository.update_report_theme(
        chat_id,
        payload.theme,
        premium_allowed=True,
    )
    return {"report_card_theme": payload.theme}


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def record_premium_event(
    payload: VipProductEventRequest,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    if payload.event_type not in ALLOWED_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported VIP event",
        )
    try:
        event = await request.app.state.vip_product_event_repository.record(
            user_id=user.telegram_id,
            event_type=payload.event_type,
            source=payload.source,
            feature_key=payload.feature_key,
            metadata=payload.metadata,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return {"event": event}
