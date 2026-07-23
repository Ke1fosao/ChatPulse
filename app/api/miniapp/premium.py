from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.repositories.vip_product_events import ALLOWED_EVENT_TYPES

router = APIRouter(prefix="/api/miniapp/v1/premium", tags=["premium-context"])


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


async def _account(request: Request, user_id: int):
    is_owner = await request.app.state.owner_repository.is_owner(user_id)
    return await request.app.state.owner_panel_repository.get_account_access(
        user_id,
        is_owner=is_owner,
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
