from copy import deepcopy

from aiogram import Dispatcher, Router

from app.bot.routers.groups import router as groups_router
from app.bot.routers.payments import router as payments_router
from app.bot.routers.private import router as private_router
from app.bot.routers.reactions import router as reactions_router
from app.bot.routers.settings import router as settings_router
from app.repositories.activity import ActivityRepository
from app.repositories.billing import BillingRepository
from app.repositories.gamification_v2 import AchievementGamificationRepository
from app.repositories.miniapp_v2 import AchievementMiniAppRepository
from app.repositories.owner import OwnerRepository

ROUTER_TEMPLATES: tuple[Router, ...] = (
    payments_router,
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
    owner_repository: OwnerRepository | None = None,
    billing_repository: BillingRepository | None = None,
) -> Dispatcher:
    dispatcher = Dispatcher()
    resolved_owner_repository = owner_repository or OwnerRepository(repository._session_factory)
    resolved_billing_repository = billing_repository or BillingRepository(
        repository._session_factory
    )
    dispatcher["repository"] = repository
    dispatcher["gamification_repository"] = AchievementGamificationRepository(
        repository._session_factory
    )
    dispatcher["miniapp_repository"] = AchievementMiniAppRepository(repository._session_factory)
    dispatcher["owner_repository"] = resolved_owner_repository
    dispatcher["billing_repository"] = resolved_billing_repository
    dispatcher["default_timezone"] = default_timezone
    dispatcher["fingerprint_secret"] = fingerprint_secret
    dispatcher["miniapp_url"] = miniapp_url
    for router_template in ROUTER_TEMPLATES:
        dispatcher.include_router(deepcopy(router_template))
    return dispatcher
