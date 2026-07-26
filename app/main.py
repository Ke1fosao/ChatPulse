import hmac
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import MenuButtonWebApp, Update, WebAppInfo
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse

from app.api.billing.routes import router as billing_router
from app.api.internal_achievements import router as internal_achievement_router
from app.api.miniapp.achievements import router as miniapp_achievements_router
from app.api.miniapp.featured import router as featured_achievement_router
from app.api.miniapp.group_settings import router as miniapp_group_settings_router
from app.api.miniapp.groups import router as miniapp_groups_router
from app.api.miniapp.home import router as miniapp_home_router
from app.api.miniapp.onboarding import router as onboarding_router
from app.api.miniapp.premium import router as premium_router
from app.api.miniapp.profile import router as miniapp_profile_router
from app.api.owner.revenue import router as owner_revenue_router
from app.api.owner.routes import router as owner_router
from app.bot.setup import build_dispatcher
from app.config import Settings, get_settings
from app.database import Database
from app.repositories.achievements import AchievementRepository
from app.repositories.activity import ActivityRepository
from app.repositories.billing import BillingRepository
from app.repositories.engagement import EngagementRepository
from app.repositories.featured_achievements import FeaturedAchievementRepository
from app.repositories.groups_v2 import GroupsV2Repository
from app.repositories.miniapp import MiniAppRepository
from app.repositories.miniapp_gamification import MiniAppGamificationRepository
from app.repositories.owner import OwnerRepository
from app.repositories.owner_panel import OwnerPanelRepository
from app.repositories.owner_revenue import OwnerRevenueRepository
from app.repositories.update_delivery import UpdateClaim, UpdateDeliveryRepository
from app.repositories.user_control import UserControlRepository
from app.repositories.vip_product_events import VipProductEventRepository
from app.services.group_settings import GroupSettingsService
from app.services.owner_payments import OwnerPaymentService
from app.services.retention_lifecycle import RetentionLifecycleService
from app.services.telegram_access import TelegramAccessService
from app.services.vip_lifecycle import VipLifecycleService
from app.services.weekly_reports import send_due_weekly_reports
from app.version import APP_VERSION

logger = logging.getLogger("chatpulse.webhook")

_INDEX_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "X-ChatPulse-Version": APP_VERSION,
}


def _miniapp_url(settings: Settings) -> str | None:
    if not settings.webhook_base_url:
        return None
    return f"{settings.webhook_base_url.rstrip('/')}/miniapp?v={APP_VERSION}"


def _miniapp_dist() -> Path | None:
    candidates = [
        Path(os.getenv("MINIAPP_DIST_DIR", "/app/miniapp_dist")),
        Path(__file__).resolve().parent.parent / "miniapp" / "dist",
    ]
    return next((path for path in candidates if path.is_dir()), None)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    miniapp_url = _miniapp_url(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = Database(resolved_settings.database_url)
        if resolved_settings.database_url.startswith("sqlite"):
            await database.create_schema()
        repository = ActivityRepository(database.session_factory)
        update_delivery_repository = UpdateDeliveryRepository(database.session_factory)
        gamification_repository = MiniAppGamificationRepository(database.session_factory)
        miniapp_repository = MiniAppRepository(database.session_factory)
        groups_v2_repository = GroupsV2Repository(
            database.session_factory,
            miniapp_repository=miniapp_repository,
        )
        achievement_repository = AchievementRepository(database.session_factory)
        featured_achievement_repository = FeaturedAchievementRepository(database.session_factory)
        owner_repository = OwnerRepository(
            database.session_factory,
            allowed_owner_id=resolved_settings.owner_telegram_id,
        )
        owner_panel_repository = OwnerPanelRepository(database.session_factory)
        owner_revenue_repository = OwnerRevenueRepository(database.session_factory)
        user_control_repository = UserControlRepository(database.session_factory)
        owner_payment_service = OwnerPaymentService(database.session_factory)
        group_settings_service = GroupSettingsService(database.session_factory)
        billing_repository = BillingRepository(database.session_factory)
        engagement_repository = EngagementRepository(database.session_factory)
        vip_product_event_repository = VipProductEventRepository(database.session_factory)
        vip_lifecycle_service = VipLifecycleService(database.session_factory)
        retention_lifecycle_service = RetentionLifecycleService(
            database.session_factory,
            miniapp_url=miniapp_url,
        )
        bot = Bot(resolved_settings.bot_token)
        telegram_access_service = TelegramAccessService(
            bot,
            owner_repository=owner_repository,
        )
        dispatcher = build_dispatcher(
            repository,
            default_timezone=resolved_settings.default_timezone,
            fingerprint_secret=resolved_settings.webhook_header_secret,
            miniapp_url=miniapp_url,
            owner_repository=owner_repository,
            billing_repository=billing_repository,
            engagement_repository=engagement_repository,
            user_control_repository=user_control_repository,
        )

        app.state.database = database
        app.state.repository = repository
        app.state.update_delivery_repository = update_delivery_repository
        app.state.gamification_repository = gamification_repository
        app.state.miniapp_repository = miniapp_repository
        app.state.groups_v2_repository = groups_v2_repository
        app.state.achievement_repository = achievement_repository
        app.state.featured_achievement_repository = featured_achievement_repository
        app.state.owner_repository = owner_repository
        app.state.owner_panel_repository = owner_panel_repository
        app.state.owner_revenue_repository = owner_revenue_repository
        app.state.user_control_repository = user_control_repository
        app.state.owner_payment_service = owner_payment_service
        app.state.group_settings_service = group_settings_service
        app.state.billing_repository = billing_repository
        app.state.engagement_repository = engagement_repository
        app.state.vip_product_event_repository = vip_product_event_repository
        app.state.vip_lifecycle_service = vip_lifecycle_service
        app.state.retention_lifecycle_service = retention_lifecycle_service
        app.state.telegram_access_service = telegram_access_service
        app.state.bot = bot
        app.state.dispatcher = dispatcher
        app.state.miniapp_url = miniapp_url
        app.state.bot_username = None
        app.state.initialized = True

        if resolved_settings.webhook_url:
            await bot.set_webhook(
                resolved_settings.webhook_url,
                secret_token=resolved_settings.webhook_header_secret,
                allowed_updates=dispatcher.resolve_used_update_types(),
                max_connections=1,
            )
        if miniapp_url:
            try:
                bot_info = await bot.get_me()
                app.state.bot_username = bot_info.username
                await bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="Відкрити ChatPulse",
                        web_app=WebAppInfo(url=miniapp_url),
                    )
                )
            except Exception:
                logger.exception("miniapp_menu_button_setup_failed")

        try:
            yield
        finally:
            app.state.initialized = False
            await bot.session.close()
            await database.dispose()

    app = FastAPI(title="ChatPulse", version=APP_VERSION, lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.initialized = False
    app.include_router(miniapp_home_router)
    app.include_router(miniapp_profile_router)
    app.include_router(miniapp_achievements_router)
    app.include_router(miniapp_groups_router)
    app.include_router(miniapp_group_settings_router)
    app.include_router(onboarding_router)
    app.include_router(featured_achievement_router)
    app.include_router(premium_router)
    app.include_router(billing_router)
    app.include_router(owner_router)
    app.include_router(owner_revenue_router)
    app.include_router(internal_achievement_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "chatpulse", "version": APP_VERSION}

    @app.get("/ready")
    async def ready(request: Request) -> dict[str, str | dict[str, str]]:
        if not getattr(request.app.state, "initialized", False):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "not_ready",
                    "components": {"application": "starting", "database": "unknown"},
                },
            )
        try:
            await request.app.state.database.ping()
        except Exception as error:
            logger.warning("readiness_database_failed error=%s", error.__class__.__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "not_ready",
                    "components": {"application": "ready", "database": "unavailable"},
                },
            ) from error
        return {
            "status": "ready",
            "components": {"application": "ready", "database": "ready"},
        }

    @app.post(resolved_settings.webhook_path)
    async def telegram_webhook(
        request: Request,
        telegram_secret: str | None = Header(
            default=None,
            alias="X-Telegram-Bot-Api-Secret-Token",
        ),
    ) -> dict[str, bool]:
        expected_secret = resolved_settings.webhook_header_secret
        if telegram_secret is None or not hmac.compare_digest(
            telegram_secret,
            expected_secret,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook secret",
            )

        payload: dict[str, Any] = await request.json()
        bot: Bot = request.app.state.bot
        dispatcher: Dispatcher = request.app.state.dispatcher
        delivery: UpdateDeliveryRepository = request.app.state.update_delivery_repository
        update_type = next((key for key in payload if key != "update_id"), "unknown")
        update_id = payload.get("update_id")
        if isinstance(update_id, int):
            claim = await delivery.begin_update(update_id, update_type)
            if claim is UpdateClaim.COMPLETED_DUPLICATE:
                return {"ok": True, "duplicate": True}
            if claim is UpdateClaim.IN_PROGRESS:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Telegram update is already being processed",
                    headers={"Retry-After": "5"},
                )

        try:
            update = Update.model_validate(payload, context={"bot": bot})
            await dispatcher.feed_update(bot, update)
        except Exception as error:
            if isinstance(update_id, int):
                await delivery.fail_update(update_id, error.__class__.__name__)
            logger.exception(
                "telegram_update_failed update_id=%s update_type=%s",
                update_id,
                update_type,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Telegram update processing failed",
            ) from error

        if isinstance(update_id, int):
            await delivery.complete_update(update_id)
        return {"ok": True}

    def require_scheduler_secret(value: str | None) -> None:
        expected_secret = resolved_settings.scheduler_secret
        if not expected_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler secret is not configured",
            )
        if value is None or not hmac.compare_digest(value, expected_secret):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid scheduler secret",
            )

    @app.post("/internal/weekly-reports")
    async def weekly_reports(
        request: Request,
        scheduler_secret: str | None = Header(
            default=None,
            alias="X-ChatPulse-Scheduler-Secret",
        ),
    ) -> dict[str, int | bool]:
        require_scheduler_secret(scheduler_secret)
        sent = await send_due_weekly_reports(
            request.app.state.bot,
            request.app.state.repository,
            retention_service=request.app.state.retention_lifecycle_service,
        )
        return {"ok": True, "sent": sent}

    @app.post("/internal/vip-lifecycle")
    async def vip_lifecycle(
        request: Request,
        scheduler_secret: str | None = Header(
            default=None,
            alias="X-ChatPulse-Scheduler-Secret",
        ),
    ) -> dict[str, int | bool]:
        require_scheduler_secret(scheduler_secret)
        vip_result = await request.app.state.vip_lifecycle_service.send_due(request.app.state.bot)
        retention_result = await request.app.state.retention_lifecycle_service.send_due(
            request.app.state.bot
        )
        return {"ok": True, **vip_result, **retention_result}

    @app.get("/miniapp", include_in_schema=False)
    @app.get("/miniapp/", include_in_schema=False)
    @app.get("/miniapp/{asset_path:path}", include_in_schema=False)
    async def miniapp_static(asset_path: str = ""):
        dist = _miniapp_dist()
        if dist is None:
            return HTMLResponse(
                "<!doctype html><html lang='uk'><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<body style='margin:0;background:#090b12;color:#fff;font-family:system-ui;"
                "display:grid;place-items:center;min-height:100vh;text-align:center;padding:24px'>"
                "<main><h1>ChatPulse Mini App</h1><p style='color:#9aa1b4'>"
                "Frontend build відсутній у локальному backend-only "
                "режимі.</p></main></body></html>",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers=_INDEX_CACHE_HEADERS,
            )

        safe_path = Path(asset_path)
        if safe_path.is_absolute() or ".." in safe_path.parts:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        requested = dist / safe_path
        is_asset_request = bool(asset_path) and (
            asset_path.startswith("assets/") or "." in safe_path.name
        )
        if is_asset_request:
            if requested.is_file():
                cache_headers = (
                    {
                        "Cache-Control": "public, max-age=31536000, immutable",
                        "X-ChatPulse-Version": APP_VERSION,
                    }
                    if asset_path.startswith("assets/")
                    else _INDEX_CACHE_HEADERS
                )
                return FileResponse(requested, headers=cache_headers)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        index = dist / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return FileResponse(
            index,
            media_type="text/html",
            headers=_INDEX_CACHE_HEADERS,
        )

    return app
