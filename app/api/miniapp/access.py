from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.services.telegram_access import TelegramAccessService


@dataclass(frozen=True, slots=True)
class GroupAccessSnapshot:
    is_member: bool
    is_admin: bool
    bot_status: str | None


async def resolve_group_access(
    access_service: TelegramAccessService | Any,
    *,
    user_id: int,
    chat_ids: Sequence[int],
    concurrency: int = 8,
) -> dict[int, GroupAccessSnapshot]:
    if concurrency < 1:
        raise ValueError("concurrency must be positive")

    semaphore = asyncio.Semaphore(concurrency)

    async def limited(call):
        async with semaphore:
            return await call

    async def resolve(chat_id: int) -> tuple[int, GroupAccessSnapshot]:
        member_call = limited(access_service.check_member(chat_id, user_id))
        admin_call = limited(access_service.check_admin(chat_id, user_id))
        get_bot_status = getattr(access_service, "get_bot_status", None)
        bot_call = (
            limited(get_bot_status(chat_id))
            if callable(get_bot_status)
            else asyncio.sleep(0, result=None)
        )
        is_member, is_admin, bot_status = await asyncio.gather(
            member_call,
            admin_call,
            bot_call,
        )
        return chat_id, GroupAccessSnapshot(
            is_member=bool(is_member),
            is_admin=bool(is_admin),
            bot_status=str(bot_status) if bot_status is not None else None,
        )

    unique_ids = list(dict.fromkeys(int(chat_id) for chat_id in chat_ids))
    pairs = await asyncio.gather(*(resolve(chat_id) for chat_id in unique_ids))
    return dict(pairs)


async def is_current_admin(request: Any, chat_id: int, user_id: int) -> bool:
    return await request.app.state.telegram_access_service.check_admin(chat_id, user_id)


async def admin_display_flag(request: Any, chat_id: int, user_id: int) -> bool:
    if not request.app.state.settings.webhook_base_url:
        return False
    return await is_current_admin(request, chat_id, user_id)


async def require_current_member(request: Any, chat_id: int, user_id: int) -> None:
    from fastapi import HTTPException, status

    if not request.app.state.settings.webhook_base_url:
        return
    if not await request.app.state.telegram_access_service.check_member(chat_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Групу не знайдено або доступ відсутній.",
        )


async def require_admin(request: Any, chat_id: int, user_id: int) -> None:
    from fastapi import HTTPException, status

    if not await is_current_admin(request, chat_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ця дія доступна лише адміністраторам групи.",
        )


def not_found():
    from fastapi import HTTPException, status

    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Групу не знайдено або доступ відсутній.",
    )


async def account_payload(request: Any, user_id: int) -> dict[str, Any]:
    is_owner = await request.app.state.owner_repository.is_owner(user_id)
    account = await request.app.state.owner_panel_repository.get_account_access(
        user_id,
        is_owner=is_owner,
    )
    return account.to_dict()
