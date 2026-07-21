from aiogram import Dispatcher

from app.bot.routers.groups import router as groups_router
from app.bot.routers.private import router as private_router
from app.bot.routers.reactions import router as reactions_router
from app.bot.routers.settings import router as settings_router
from app.repositories.activity import ActivityRepository


def build_dispatcher(
    repository: ActivityRepository,
    *,
    default_timezone: str,
) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher["repository"] = repository
    dispatcher["default_timezone"] = default_timezone
    dispatcher.include_router(private_router)
    dispatcher.include_router(settings_router)
    dispatcher.include_router(reactions_router)
    dispatcher.include_router(groups_router)
    return dispatcher
