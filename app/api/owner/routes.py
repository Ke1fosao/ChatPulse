from datetime import datetime
from typing import Annotated, Literal

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

router = APIRouter(prefix="/api/owner/v1", tags=["owner"])


def _repository(request: Request) -> OwnerPanelRepository:
    return request.app.state.owner_panel_repository


def _user_repository(request: Request) -> UserControlRepository:
    return request.app.state.user_control_repository


def _vip_service(request: Request) -> AdminVipService:
    return AdminVipService(request.app.state.database.session_factory)


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


@router.get("/session")
async def owner_session(
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    account = build_account_access(
        is_owner=actor.is_owner,
        vip_is_active=False,
        vip_expires_at=None,
    )
    return {
        "owner": {
            "telegram_id": user.telegram_id,
            "display_name": user.display_name,
            "username": user.username,
            "photo_url": user.photo_url,
        },
        "actor": actor.to_dict(),
        "account": account.to_dict(),
    }


@router.get("/overview")
async def owner_overview(
    request: Request,
    _user: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    return await _repository(request).get_overview()


@router.get("/users")
async def owner_users(
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
    q: Annotated[str | None, Query(max_length=128)] = None,
    vip: Annotated[Literal["all", "active", "inactive", "expiring"], Query()] = "all",
    account_status: Annotated[Literal["all", "active", "inactive", "blocked"], Query()] = "all",
    role: Annotated[Literal["all", "owner", "admin", "moderator", "support", "none"], Query()] = "all",
    payment: Annotated[Literal["all", "paid", "never"], Query()] = "all",
    tag: Annotated[str | None, Query(max_length=32)] = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort: Annotated[
        Literal[
            "activity_desc",
            "activity_asc",
            "created_desc",
            "created_asc",
            "xp_desc",
            "xp_asc",
            "groups_desc",
            "groups_asc",
            "stars_desc",
            "stars_asc",
            "vip_expiry_asc",
        ],
        Query(),
    ] = "activity_desc",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    try:
        return await _user_repository(request).list_users(
            actor,
            query=q,
            vip_filter=vip,
            status_filter=account_status,
            role_filter=role,
            payment_filter=payment,
            tag=tag,
            created_from=created_from,
            created_to=created_to,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.post("/users/bulk")
async def owner_users_bulk(
    payload: UserBulkRequest,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    succeeded: list[dict] = []
    failed: list[dict] = []
    repository = _user_repository(request)
    vip_service = _vip_service(request)

    for user_id in payload.user_ids:
        try:
            if payload.action == "grant_vip":
                result = await vip_service.grant(
                    actor,
                    user_id,
                    expires_at=payload.expires_at if payload.mode == "until" else None,
                    reason=payload.reason or "Масова видача VIP",
                )
            elif payload.action == "revoke_vip":
                result = await vip_service.revoke(
                    actor,
                    user_id,
                    reason=payload.reason or "Масове відкликання VIP",
                )
            elif payload.action == "block":
                if not actor.can("bulk.block"):
                    raise PermissionError("bulk.block")
                result = await repository.block_user(actor, user_id, payload.reason or "Масове блокування")
            elif payload.action == "unblock":
                if not actor.can("bulk.block"):
                    raise PermissionError("bulk.block")
                result = await repository.unblock_user(
                    actor,
                    user_id,
                    payload.reason or "Масове розблокування",
                )
            elif payload.action == "add_tag":
                if not actor.can("bulk.tag_message"):
                    raise PermissionError("bulk.tag_message")
                result = await repository.add_tag(actor, user_id, payload.tag or "")
            elif payload.action == "remove_tag":
                if not actor.can("bulk.tag_message"):
                    raise PermissionError("bulk.tag_message")
                result = await repository.remove_tag(actor, user_id, payload.tag or "")
            else:
                if not actor.can("bulk.tag_message"):
                    raise PermissionError("bulk.tag_message")
                result = await _send_user_message(
                    request,
                    actor,
                    user_id,
                    payload.message_text or "",
                )
            succeeded.append({"user_id": user_id, "result": result})
        except Exception as error:
            failed.append({"user_id": user_id, "error": str(error)})

    return {
        "action": payload.action,
        "requested": len(payload.user_ids),
        "succeeded": succeeded,
        "failed": failed,
    }


@router.get("/users/{telegram_user_id}")
async def owner_user_detail(
    telegram_user_id: int,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        payload = await _user_repository(request).get_user_detail(actor, telegram_user_id)
    except Exception as error:
        _raise_repository_error(error)
        raise
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return payload


@router.post("/users/{telegram_user_id}/vip")
async def grant_vip(
    telegram_user_id: int,
    payload: VipGrantRequest,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        return await _vip_service(request).grant(
            actor,
            telegram_user_id,
            expires_at=payload.expires_at if payload.mode == "until" else None,
            reason=payload.reason,
        )
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.delete("/users/{telegram_user_id}/vip")
async def revoke_vip(
    telegram_user_id: int,
    payload: VipRevokeRequest,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        return await _vip_service(request).revoke(
            actor,
            telegram_user_id,
            reason=payload.reason,
        )
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.post("/users/{telegram_user_id}/block")
async def block_user(
    telegram_user_id: int,
    payload: UserBlockRequest,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        return await _user_repository(request).block_user(actor, telegram_user_id, payload.reason)
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.post("/users/{telegram_user_id}/unblock")
async def unblock_user(
    telegram_user_id: int,
    payload: UserUnblockRequest,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        return await _user_repository(request).unblock_user(actor, telegram_user_id, payload.reason)
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.patch("/users/{telegram_user_id}/note")
async def update_user_note(
    telegram_user_id: int,
    payload: UserNoteRequest,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        return await _user_repository(request).set_note(actor, telegram_user_id, payload.note)
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.post("/users/{telegram_user_id}/tags")
async def add_user_tag(
    telegram_user_id: int,
    payload: UserTagRequest,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        return await _user_repository(request).add_tag(actor, telegram_user_id, payload.tag)
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.delete("/users/{telegram_user_id}/tags/{tag}")
async def remove_user_tag(
    telegram_user_id: int,
    tag: str,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        return await _user_repository(request).remove_tag(actor, telegram_user_id, tag)
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.post("/users/{telegram_user_id}/xp-adjustments")
async def adjust_user_xp(
    telegram_user_id: int,
    payload: UserXpAdjustmentRequest,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        return await _user_repository(request).adjust_xp(
            actor,
            telegram_user_id,
            payload.amount,
            payload.reason,
            chat_id=payload.telegram_chat_id,
        )
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.put("/users/{telegram_user_id}/role")
async def update_user_role(
    telegram_user_id: int,
    payload: UserRoleRequest,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        return await _user_repository(request).set_role(actor, telegram_user_id, payload.role)
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.delete("/users/{telegram_user_id}/role")
async def remove_user_role(
    telegram_user_id: int,
    payload: UserRoleRemoveRequest,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        return await _user_repository(request).remove_role(actor, telegram_user_id, payload.reason)
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.post("/users/{telegram_user_id}/messages")
async def message_user(
    telegram_user_id: int,
    payload: UserMessageRequest,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
) -> dict:
    try:
        return await _send_user_message(request, actor, telegram_user_id, payload.message_text)
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.get("/users/{telegram_user_id}/audit")
async def user_audit(
    telegram_user_id: int,
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, list[dict]]:
    try:
        items = await _user_repository(request).list_user_audit(actor, telegram_user_id, limit=limit)
        return {"items": items}
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.get("/groups")
async def owner_groups(
    request: Request,
    _user: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
    q: Annotated[str | None, Query(max_length=128)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return await _repository(request).list_groups(query=q, limit=limit, offset=offset)


@router.patch("/groups/{chat_id}")
async def update_owner_group(
    chat_id: int,
    payload: OwnerGroupUpdate,
    request: Request,
    owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    try:
        return await _repository(request).update_group(
            owner_user_id=owner.telegram_id,
            chat_id=chat_id,
            values=payload.model_dump(exclude={"confirmation"}, exclude_none=True),
        )
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.get("/audit")
async def owner_audit(
    request: Request,
    _user: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, list[dict]]:
    return {"items": await _repository(request).list_audit(limit=limit)}
