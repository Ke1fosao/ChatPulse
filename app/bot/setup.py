from copy import deepcopy

from aiogram import Dispatcher, Router

from app.bot.routers.groups import router as groups_router
from app.bot.routers.private import router as private_router
from app.bot.routers.reactions import router as reactions_router
from app.bot.routers.settings import router as settings_router
from app.repositories.activity import ActivityRepository
from app.repositories.gamification import GamificationRepository
from app.repositories.miniapp import MiniAppRepository

ROUTER_TEMPLATES: tuple[Router, ...] = (
    private_router,
    settings_router,
    reactions_router,
    groups_router,
)


def build_dispatcher(
    repository: ActivityRepository,
    *,
    default_timezone: str,
    fingerprint_secret: str = "chatpulse-local-fingerprint",
    miniapp_url: str | None = None,
) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher["repository"] = repository
    dispatcher["gamification_repository"] = GamificationRepository(repository._session_factory)
    dispatcher["miniapp_repository"] = MiniAppRepository(repository._session_factory)
    dispatcher["default_timezone"] = default_timezone
    dispatcher["fingerprint_secret"] = fingerprint_secret
    dispatcher["miniapp_url"] = miniapp_url
    for router_template in ROUTER_TEMPLATES:
        dispatcher.include_router(deepcopy(router_template))
    return dispatcher
