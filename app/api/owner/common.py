# ruff: noqa: F401, F403, F405, F821, I001
from datetime import datetime
from typing import Annotated, Literal
import sys

from aiogram.exceptions import TelegramAPIError
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.api.owner.dependencies import get_admin_actor, get_owner_user
from app.api.owner.schemas import (
    OwnerGroupUpdate,
    UserBlockRequest,
    UserBulkRequest,
    UserMessageRequest,
    UserNoteRequest,
    UserRoleRemoveRequest,
    UserRoleRequest,
    UserTagRequest,
    UserUnblockRequest,
    UserXpAdjustmentRequest,
    VipGrantRequest,
    VipRevokeRequest,
)
from app.repositories.owner_panel import OwnerPanelRepository
from app.repositories.user_control import UserControlRepository
from app.services.admin_access import AdminActor
from app.services.admin_vip import AdminVipService
from app.services.entitlements import build_account_access


def _repository(request: Request) -> OwnerPanelRepository:
    return request.app.state.owner_panel_repository


def _user_repository(request: Request) -> UserControlRepository:
    return request.app.state.user_control_repository


def _default_vip_service(request: Request) -> AdminVipService:
    return AdminVipService(request.app.state.database.session_factory)


def _vip_service(request: Request) -> AdminVipService:
    routes_module = sys.modules.get("app.api.owner.routes")
    override = getattr(routes_module, "_vip_service", None) if routes_module else None
    if override is not None and override is not _vip_service:
        return override(request)
    return _default_vip_service(request)


def _raise_repository_error(error: Exception) -> None:
    if isinstance(error, PermissionError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PERMISSION_DENIED",
                "message": "Недостатньо прав для цієї дії.",
            },
        ) from error
    if isinstance(error, LookupError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    if isinstance(error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    raise error


async def _send_user_message(
    request: Request,
    actor: AdminActor,
    telegram_user_id: int,
    message_text: str,
) -> dict:
    repository = _user_repository(request)
    delivery = await repository.create_message_delivery(actor, telegram_user_id, message_text)
    try:
        await request.app.state.bot.send_message(
            chat_id=telegram_user_id,
            text=message_text.strip(),
        )
    except TelegramAPIError as error:
        return await repository.finish_message_delivery(
            actor,
            int(delivery["id"]),
            sent=False,
            safe_error=error.__class__.__name__,
        )
    except Exception:
        return await repository.finish_message_delivery(
            actor,
            int(delivery["id"]),
            sent=False,
            safe_error="telegram_delivery_failed",
        )
    return await repository.finish_message_delivery(actor, int(delivery["id"]), sent=True)
