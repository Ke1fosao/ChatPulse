from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from app.api.miniapp.auth import MiniAppAuthError, TelegramMiniAppUser, validate_init_data
from app.api.rate_limit import enforce_rate_limit, remote_address
from app.config import Settings
from app.repositories.user_control import UserControlRepository


async def _record_invalid_auth(request: Request) -> None:
    await enforce_rate_limit(request, "invalid_auth", remote_address(request))


async def get_miniapp_user(
    request: Request,
    init_data: Annotated[str | None, Header(alias="X-Telegram-Init-Data")] = None,
) -> TelegramMiniAppUser:
    if not init_data:
        await _record_invalid_auth(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Відкрийте ChatPulse через Telegram.",
        )

    settings: Settings = request.app.state.settings
    try:
        user = validate_init_data(init_data, settings.bot_token)
    except MiniAppAuthError as error:
        await _record_invalid_auth(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error

    request.state.telegram_user = user
    policy = "miniapp_read" if request.method in {"GET", "HEAD", "OPTIONS"} else "miniapp_write"
    await enforce_rate_limit(request, policy, str(user.telegram_id))

    repository: UserControlRepository | None = getattr(
        request.app.state,
        "user_control_repository",
        None,
    )
    if repository is not None:
        block_info = await repository.get_block_info(user.telegram_id)
        if block_info is not None:
            await repository.record_blocked_access(user.telegram_id, "miniapp")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ACCOUNT_BLOCKED",
                    "message": "Доступ до ChatPulse обмежено адміністратором.",
                    "reason": block_info.get("reason"),
                },
            )
    return user
