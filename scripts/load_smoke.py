from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import httpx

from app.config import Settings
from app.main import create_app
from app.models import User
from load.identity import signed_init_data


async def _seed_user(session_factory, user_id: int) -> None:
    async with session_factory() as session:
        session.add(
            User(
                telegram_id=user_id,
                username="load_test",
                first_name="Load",
                last_name="Test",
                language_code="uk",
            )
        )
        await session.commit()


async def main() -> None:
    user_id = 987_654_321
    bot_token = "123456:load-smoke-token"
    with tempfile.TemporaryDirectory() as directory:
        redis_url = os.getenv("TEST_REDIS_URL")
        settings = Settings(
            bot_token=bot_token,
            webhook_path_secret="load-path-secret",
            webhook_header_secret="load-header-secret",
            scheduler_secret="load-scheduler-secret",
            database_url=f"sqlite+aiosqlite:///{Path(directory) / 'load.db'}",
            environment="test",
            redis_url=redis_url,
            redis_required=bool(redis_url),
            redis_key_prefix=f"chatpulse:load-smoke:{os.getpid()}",
        )
        app = create_app(settings)
        async with app.router.lifespan_context(app):
            await _seed_user(app.state.database.session_factory, user_id)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                responses = await asyncio.gather(
                    *(client.get("/health") for _ in range(40)),
                    *(client.get("/ready") for _ in range(20)),
                )
                failures = [response for response in responses if response.status_code != 200]
                if failures:
                    raise SystemExit(f"load smoke failures: {[r.status_code for r in failures]}")

                init_data = signed_init_data(bot_token, user_id)
                home = await client.get(
                    "/api/miniapp/v1/home",
                    headers={"X-Telegram-Init-Data": init_data},
                )
                if home.status_code != 200:
                    raise SystemExit(f"authenticated read failed: {home.status_code} {home.text}")

                webhook_headers = {
                    "X-Telegram-Bot-Api-Secret-Token": settings.webhook_header_secret
                }
                payload = {"update_id": 991_001}
                delivered = await client.post(
                    settings.webhook_path,
                    headers=webhook_headers,
                    json=payload,
                )
                duplicate = await client.post(
                    settings.webhook_path,
                    headers=webhook_headers,
                    json=payload,
                )
                if delivered.status_code != 200 or duplicate.json().get("duplicate") is not True:
                    raise SystemExit("duplicate webhook invariant failed")

                if redis_url:
                    invalid = [
                        await client.get(
                            "/api/miniapp/v1/home",
                            headers={"X-Forwarded-For": "203.0.113.10"},
                        )
                        for _ in range(31)
                    ]
                    if [response.status_code for response in invalid[:30]] != [401] * 30:
                        raise SystemExit("invalid-auth budget rejected too early")
                    if invalid[30].status_code != 429:
                        raise SystemExit("invalid-auth rate limit did not activate")

                ready = await client.get("/ready")
                if ready.json().get("status") != "ready":
                    raise SystemExit("application did not remain ready")
    print("load_smoke_ok=true")


if __name__ == "__main__":
    os.environ.setdefault("ENVIRONMENT", "test")
    asyncio.run(main())
