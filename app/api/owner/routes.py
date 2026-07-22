from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.owner.dependencies import get_owner_user
from app.api.owner.schemas import OwnerGroupUpdate, VipGrantRequest, VipRevokeRequest
from app.repositories.owner_panel import OwnerPanelRepository
from app.services.entitlements import build_account_access

router = APIRouter(prefix="/api/owner/v1", tags=["owner"])


def _repository(request: Request) -> OwnerPanelRepository:
    return request.app.state.owner_panel_repository


def _raise_repository_error(error: Exception) -> None:
    if isinstance(error, PermissionError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner authorization failed.",
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


@router.get("/session")
async def owner_session(
    user: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    account = build_account_access(
        is_owner=True,
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
    _user: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
    q: Annotated[str | None, Query(max_length=128)] = None,
    vip: Annotated[Literal["all", "active", "inactive"], Query()] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return await _repository(request).list_users(
        query=q,
        vip_filter=vip,
        limit=limit,
        offset=offset,
    )


@router.get("/users/{telegram_user_id}")
async def owner_user_detail(
    telegram_user_id: int,
    request: Request,
    _user: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    payload = await _repository(request).get_user(telegram_user_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return payload


@router.post("/users/{telegram_user_id}/vip")
async def grant_vip(
    telegram_user_id: int,
    payload: VipGrantRequest,
    request: Request,
    owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    if telegram_user_id == owner.telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Власника не можна перетворити на VIP-клієнта.",
        )
    try:
        return await _repository(request).grant_vip(
            owner_user_id=owner.telegram_id,
            target_user_id=telegram_user_id,
            expires_at=payload.expires_at if payload.mode == "until" else None,
            reason=payload.reason.strip(),
        )
    except Exception as error:
        _raise_repository_error(error)
        raise


@router.delete("/users/{telegram_user_id}/vip")
async def revoke_vip(
    telegram_user_id: int,
    payload: VipRevokeRequest,
    request: Request,
    owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    if telegram_user_id == owner.telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Роль власника не можна змінити через панель.",
        )
    try:
        return await _repository(request).revoke_vip(
            owner_user_id=owner.telegram_id,
            target_user_id=telegram_user_id,
            reason=payload.reason.strip(),
        )
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
