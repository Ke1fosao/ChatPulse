from copy import deepcopy

from aiogram import Dispatcher, Router

from app.bot.routers.groups import router as groups_router
from app.bot.routers.private import router as private_router
from app.bot.routers.reactions import router as reactions_router
from app.bot.routers.settings import router as settings_router
from app.repositories.activity import ActivityRepository

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
) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher["repository"] = repository
    dispatcher["default_timezone"] = default_timezone
    for router_template in ROUTER_TEMPLATES:
        dispatcher.include_router(deepcopy(router_template))
    return dispatcher
