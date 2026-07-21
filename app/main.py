import hmac
from contextlib import asynccontextmanager
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request, status

from app.bot.setup import build_dispatcher
from app.config import Settings, get_settings
from app.database import Database
from app.repositories.activity import ActivityRepository


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = Database(resolved_settings.database_url)
        await database.create_schema()
        repository = ActivityRepository(database.session_factory)
        bot = Bot(resolved_settings.bot_token)
        dispatcher = build_dispatcher(
            repository,
            default_timezone=resolved_settings.default_timezone,
        )

        app.state.database = database
        app.state.repository = repository
        app.state.bot = bot
        app.state.dispatcher = dispatcher

        if resolved_settings.webhook_url:
            await bot.set_webhook(
                resolved_settings.webhook_url,
                secret_token=resolved_settings.webhook_header_secret,
                allowed_updates=dispatcher.resolve_used_update_types(),
            )

        try:
            yield
        finally:
            await bot.session.close()
            await database.dispose()

    app = FastAPI(title="ChatPulse", version="0.1.0", lifespan=lifespan)
    app.state.settings = resolved_settings

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "chatpulse"}

    @app.post(resolved_settings.webhook_path)
    async def telegram_webhook(
        request: Request,
        telegram_secret: str | None = Header(
            default=None,
            alias="X-Telegram-Bot-Api-Secret-Token",
        ),
    ) -> dict[str, bool]:
        expected_secret = resolved_settings.webhook_header_secret
        if telegram_secret is None or not hmac.compare_digest(telegram_secret, expected_secret):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook secret",
            )

        payload: dict[str, Any] = await request.json()
        bot: Bot = request.app.state.bot
        dispatcher: Dispatcher = request.app.state.dispatcher
        update = Update.model_validate(payload, context={"bot": bot})
        await dispatcher.feed_update(bot, update)
        return {"ok": True}

    return app
