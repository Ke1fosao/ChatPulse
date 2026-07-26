from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.repositories.engagement import EngagementRepository

router = APIRouter(prefix="/api/miniapp/v1", tags=["miniapp-onboarding"])


async def _bot_username(request: Request) -> str | None:
    cached = getattr(request.app.state, "bot_username", None)
    if cached:
        return str(cached)
    try:
        bot_info = await request.app.state.bot.get_me()
    except Exception:
        return None
    username = bot_info.username
    if username:
        request.app.state.bot_username = username
    return username


@router.get("/onboarding")
async def onboarding(
    request: Request,
    user: Annotated[TelegramMiniAppUser, Depends(get_miniapp_user)],
) -> dict:
    repository: EngagementRepository = request.app.state.engagement_repository
    await repository.mark_private_started(user.telegram_id)
    return await repository.get_onboarding(
        user.telegram_id,
        bot_username=await _bot_username(request),
    )
