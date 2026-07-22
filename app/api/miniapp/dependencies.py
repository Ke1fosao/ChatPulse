from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from app.api.miniapp.auth import MiniAppAuthError, TelegramMiniAppUser, validate_init_data
from app.config import Settings


async def get_miniapp_user(
    request: Request,
    init_data: Annotated[str | None, Header(alias="X-Telegram-Init-Data")] = None,
) -> TelegramMiniAppUser:
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Відкрийте ChatPulse через Telegram.",
        )

    settings: Settings = request.app.state.settings
    try:
        return validate_init_data(init_data, settings.bot_token)
    except MiniAppAuthError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error
