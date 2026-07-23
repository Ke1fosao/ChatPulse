from __future__ import annotations

from typing import Annotated

from aiogram import Bot
from aiogram.types import LabeledPrice
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.billing.schemas import CreateInvoiceRequest, ExportPeriod, SubscriptionUpdateRequest
from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.repositories.billing import BillingRepository
from app.repositories.miniapp import MiniAppRepository
from app.repositories.owner import OwnerRepository
from app.repositories.owner_panel import OwnerPanelRepository
from app.services.analytics_exports import render_group_csv, render_group_pdf
from app.services.vip_plans import VIP_BENEFITS, VIP_PLANS, get_vip_plan

router = APIRouter(prefix="/api/miniapp/v1/vip", tags=["vip-billing"])


def _billing(request: Request) -> BillingRepository:
    return request.app.state.billing_repository


def _miniapp(request: Request) -> MiniAppRepository:
    return request.app.state.miniapp_repository


def _owners(request: Request) -> OwnerRepository:
    return request.app.state.owner_repository


def _owner_panel(request: Request) -> OwnerPanelRepository:
    return request.app.state.owner_panel_repository


async def _account_access(request: Request, user_id: int):
    is_owner = await _owners(request).is_owner(user_id)
    return await _owner_panel(request).get_account_access(user_id, is_owner=is_owner)


async def _require_premium(request: Request, user_id: int) -> None:
    access = await _account_access(request, user_id)
    if not (access.is_owner or access.is_vip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ця функція доступна у ChatPulse VIP.",
        )


@router.get("/plans")
async def plans(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    access = await _account_access(request, user.telegram_id)
    billing_status = await _billing(request).get_status(user.telegram_id)
    trial_available = bool(billing_status["trial_available"] and not access.is_owner)
    return {
        "account": access.to_dict(),
        "billing": billing_status,
        "benefits": list(VIP_BENEFITS),
        "plans": [
            plan.to_public_dict(
                available=(trial_available if plan.code == "trial_7d" else not access.is_owner)
            )
            for plan in VIP_PLANS.values()
        ],
    }


@router.get("/history")
async def history(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> dict:
    return {"payments": await _billing(request).list_history(user.telegram_id, limit=limit)}


@router.post("/invoice")
async def create_invoice(
    payload: CreateInvoiceRequest,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, str]:
    access = await _account_access(request, user.telegram_id)
    if access.is_owner:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Власник ChatPulse уже має всі VIP-функції.",
        )
    try:
        intent = await _billing(request).create_invoice_intent(
            user.telegram_id,
            payload.plan_code,
        )
    except (ValueError, LookupError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    plan = get_vip_plan(payload.plan_code)
    bot: Bot = request.app.state.bot
    kwargs = {
        "title": plan.title,
        "description": plan.description,
        "payload": intent["payload"],
        "provider_token": None,
        "currency": "XTR",
        "prices": [LabeledPrice(label=plan.short_title, amount=plan.stars)],
    }
    if plan.subscription_period is not None:
        kwargs["subscription_period"] = plan.subscription_period
    try:
        invoice_url = await bot.create_invoice_link(**kwargs)
    except Exception as error:
        await _billing(request).invalidate_invoice(intent["payload"])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Telegram не зміг створити рахунок. Спробуй ще раз.",
        ) from error
    return {"invoice_url": invoice_url}


@router.post("/subscription")
async def update_subscription(
    payload: SubscriptionUpdateRequest,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict[str, bool]:
    control = await _billing(request).get_subscription_control(user.telegram_id)
    if control is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Активну місячну підписку не знайдено.",
        )
    bot: Bot = request.app.state.bot
    await bot.edit_user_star_subscription(
        user_id=user.telegram_id,
        telegram_payment_charge_id=control["telegram_payment_charge_id"],
        is_canceled=payload.canceled,
    )
    await _billing(request).set_subscription_canceled(
        user.telegram_id,
        canceled=payload.canceled,
    )
    return {"ok": True, "canceled": payload.canceled}


@router.get("/groups/{chat_id}/export.csv")
async def export_csv(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    period: Annotated[ExportPeriod, Query()] = "month",
) -> Response:
    await _require_premium(request, user.telegram_id)
    dashboard = await _authorized_dashboard(request, user.telegram_id, chat_id, period)
    return Response(
        content=render_group_csv(dashboard),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=chatpulse-analytics.csv"},
    )


@router.get("/groups/{chat_id}/export.pdf")
async def export_pdf(
    chat_id: int,
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    period: Annotated[ExportPeriod, Query()] = "month",
) -> Response:
    await _require_premium(request, user.telegram_id)
    dashboard = await _authorized_dashboard(request, user.telegram_id, chat_id, period)
    return Response(
        content=render_group_pdf(dashboard),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=chatpulse-analytics.pdf"},
    )


async def _authorized_dashboard(
    request: Request,
    user_id: int,
    chat_id: int,
    period: ExportPeriod,
) -> dict:
    dashboard = await _miniapp(request).get_group_dashboard(user_id, chat_id, period)
    if dashboard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )
    if request.app.state.settings.webhook_base_url:
        is_member = await request.app.state.telegram_access_service.check_member(chat_id, user_id)
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Групу не знайдено або доступ відсутній.",
            )
    return dashboard
