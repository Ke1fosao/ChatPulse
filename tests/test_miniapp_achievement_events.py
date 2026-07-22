from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.config import Settings
from app.main import create_app


def build_settings() -> Settings:
    return Settings(
        bot_token="123456:test-token",
        webhook_path_secret="path-secret",
        webhook_header_secret="header-secret",
        scheduler_secret="scheduler-secret",
        database_url="sqlite+aiosqlite:///:memory:",
    )


def current_user() -> TelegramMiniAppUser:
    return TelegramMiniAppUser(
        telegram_id=101,
        first_name="Dmytro",
        username="dmytro",
        auth_date="2026-07-22T10:00:00Z",
    )


def test_pending_events_are_scoped_to_verified_telegram_user() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(
        list_pending_events=AsyncMock(
            return_value=[
                {
                    "event_id": 7,
                    "event_type": "unlock",
                    "created_at": "2026-07-22T10:00:00+00:00",
                    "achievement": {"code": "first_steps", "rarity": "common"},
                }
            ]
        ),
        mark_seen=AsyncMock(return_value=True),
        mark_shared=AsyncMock(return_value=True),
    )

    with TestClient(app) as client:
        app.state.achievement_repository = repository
        response = client.get("/api/miniapp/v1/achievement-events?limit=5")
        seen = client.post("/api/miniapp/v1/achievement-events/7/seen")
        shared = client.post("/api/miniapp/v1/achievement-events/7/shared")

    assert response.status_code == 200
    assert response.json()["events"][0]["event_id"] == 7
    assert seen.status_code == 200
    assert shared.status_code == 200
    repository.list_pending_events.assert_awaited_once_with(101, limit=5)
    repository.mark_seen.assert_awaited_once_with(101, 7)
    repository.mark_shared.assert_awaited_once_with(101, 7)


def test_event_from_another_user_is_not_acknowledged() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(
        list_pending_events=AsyncMock(return_value=[]),
        mark_seen=AsyncMock(return_value=False),
        mark_shared=AsyncMock(return_value=False),
    )

    with TestClient(app) as client:
        app.state.achievement_repository = repository
        response = client.post("/api/miniapp/v1/achievement-events/999/seen")

    assert response.status_code == 404
    assert response.json()["detail"] == "Подію досягнення не знайдено."
    repository.mark_seen.assert_awaited_once_with(101, 999)
