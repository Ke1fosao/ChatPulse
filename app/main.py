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

from app.api.miniapp.routes import router as miniapp_router
from app.bot.setup import build_dispatcher
from app.config import Settings, get_settings
from app.database import Database
from app.repositories.activity import ActivityRepository
from app.repositories.miniapp import MiniAppRepository
from app.repositories.miniapp_gamification import MiniAppGamificationRepository
from app.services.telegram_access import TelegramAccessService
from app.services.weekly_reports import send_due_weekly_reports

logger = logging.getLogger("chatpulse.webhook")


def _miniapp_url(settings: Settings) -> str | None:
    if not settings.webhook_base_url:
        return None
    return f"{settings.webhook_base_url.rstrip('/')}/miniapp"


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
        await database.create_schema()
        repository = ActivityRepository(database.session_factory)
        gamification_repository = MiniAppGamificationRepository(database.session_factory)
        miniapp_repository = MiniAppRepository(database.session_factory)
        bot = Bot(resolved_settings.bot_token)
        telegram_access_service = TelegramAccessService(bot)
        dispatcher = build_dispatcher(
            repository,
            default_timezone=resolved_settings.default_timezone,
            fingerprint_secret=resolved_settings.webhook_header_secret,
            miniapp_url=miniapp_url,
        )

        app.state.database = database
        app.state.repository = repository
        app.state.gamification_repository = gamification_repository
        app.state.miniapp_repository = miniapp_repository
        app.state.telegram_access_service = telegram_access_service
        app.state.bot = bot
        app.state.dispatcher = dispatcher
        app.state.miniapp_url = miniapp_url

        if resolved_settings.webhook_url:
            await bot.set_webhook(
                resolved_settings.webhook_url,
                secret_token=resolved_settings.webhook_header_secret,
                allowed_updates=dispatcher.resolve_used_update_types(),
                max_connections=1,
            )
        if miniapp_url:
            try:
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
            await bot.session.close()
            await database.dispose()

    app = FastAPI(title="ChatPulse", version="0.4.0", lifespan=lifespan)
    app.state.settings = resolved_settings
    app.include_router(miniapp_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "chatpulse", "version": "0.4.0"}

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
        repository: ActivityRepository = request.app.state.repository
        update_type = next((key for key in payload if key != "update_id"), "unknown")
        update_id = payload.get("update_id")
        if isinstance(update_id, int) and not await repository.claim_update(
            update_id,
            update_type,
        ):
            return {"ok": True, "duplicate": True}

        update = Update.model_validate(payload, context={"bot": bot})
        try:
            await dispatcher.feed_update(bot, update)
        except Exception:
            logger.exception(
                "telegram_update_failed update_id=%s update_type=%s",
                update_id,
                update_type,
            )
            return {"ok": False}
        return {"ok": True}

    @app.post("/internal/weekly-reports")
    async def weekly_reports(
        request: Request,
        scheduler_secret: str | None = Header(
            default=None,
            alias="X-ChatPulse-Scheduler-Secret",
        ),
    ) -> dict[str, int | bool]:
        expected_secret = resolved_settings.scheduler_secret
        if not expected_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler secret is not configured",
            )
        if scheduler_secret is None or not hmac.compare_digest(
            scheduler_secret,
            expected_secret,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid scheduler secret",
            )
        sent = await send_due_weekly_reports(
            request.app.state.bot,
            request.app.state.repository,
        )
        return {"ok": True, "sent": sent}

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
                return FileResponse(requested)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        index = dist / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return FileResponse(index, media_type="text/html")

    return app
