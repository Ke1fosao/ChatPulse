# ruff: noqa: F401, F403, F405, F821, I001
from .common import *  # noqa: F403
from .common import (
    _raise_repository_error,
    _repository,
    _send_user_message,
    _user_repository,
    _vip_service,
)

router = APIRouter()


@router.get("/users")
async def owner_users(
    request: Request,
    actor: Annotated[AdminActor, Depends(get_admin_actor)],
    q: Annotated[str | None, Query(max_length=128)] = None,
    vip: Annotated[Literal["all", "active", "inactive", "expiring"], Query()] = "all",
    account_status: Annotated[Literal["all", "active", "inactive", "blocked"], Query()] = "all",
    role: Annotated[
        Literal["all", "owner", "admin", "moderator", "support", "none"], Query()
    ] = "all",
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
                result = await repository.block_user(
                    actor, user_id, payload.reason or "Масове блокування"
                )
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
        items = await _user_repository(request).list_user_audit(
            actor, telegram_user_id, limit=limit
        )
        return {"items": items}
    except Exception as error:
        _raise_repository_error(error)
        raise
