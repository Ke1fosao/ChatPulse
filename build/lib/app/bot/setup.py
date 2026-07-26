from copy import deepcopy

from aiogram import Dispatcher, Router

from app.bot.middlewares import BlockedUserMiddleware
from app.bot.routers.groups import router as groups_router
from app.bot.routers.onboarding import router as onboarding_router
from app.bot.routers.payments import router as payments_router
from app.bot.routers.private import router as private_router
from app.bot.routers.reactions import router as reactions_router
from app.bot.routers.settings import router as settings_router
from app.repositories.activity import ActivityRepository
from app.repositories.billing import BillingRepository
from app.repositories.engagement import EngagementRepository
from app.repositories.gamification_v2 import AchievementGamificationRepository
from app.repositories.miniapp_v2 import AchievementMiniAppRepository
from app.repositories.owner import OwnerRepository
from app.repositories.user_control import UserControlRepository

ROUTER_TEMPLATES: tuple[Router, ...] = (
    payments_router,
    onboarding_router,
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
    engagement_repository: EngagementRepository | None = None,
    user_control_repository: UserControlRepository | None = None,
) -> Dispatcher:
    dispatcher = Dispatcher()
    resolved_owner_repository = owner_repository or OwnerRepository(repository._session_factory)
    resolved_billing_repository = billing_repository or BillingRepository(
        repository._session_factory
    )
    resolved_engagement_repository = engagement_repository or EngagementRepository(
        repository._session_factory
    )
    resolved_user_control_repository = user_control_repository or UserControlRepository(
        repository._session_factory
    )
    dispatcher.update.outer_middleware(BlockedUserMiddleware(resolved_user_control_repository))
    dispatcher["repository"] = repository
    dispatcher["gamification_repository"] = AchievementGamificationRepository(
        repository._session_factory
    )
    dispatcher["miniapp_repository"] = AchievementMiniAppRepository(repository._session_factory)
    dispatcher["owner_repository"] = resolved_owner_repository
    dispatcher["billing_repository"] = resolved_billing_repository
    dispatcher["engagement_repository"] = resolved_engagement_repository
    dispatcher["user_control_repository"] = resolved_user_control_repository
    dispatcher["default_timezone"] = default_timezone
    dispatcher["fingerprint_secret"] = fingerprint_secret
    dispatcher["miniapp_url"] = miniapp_url
    for router_template in ROUTER_TEMPLATES:
        dispatcher.include_router(deepcopy(router_template))
    return dispatcher
