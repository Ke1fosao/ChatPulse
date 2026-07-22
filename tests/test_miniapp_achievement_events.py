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


def unlock_event() -> dict:
    return {
        "event_id": 7,
        "event_type": "unlock",
        "created_at": "2026-07-22T10:00:00+00:00",
        "achievement": {
            "code": "messages_100",
            "title": "Перша сотня",
            "description": "Надіслано 100 повідомлень",
            "category": "activity",
            "rarity": "uncommon",
            "scope": "group",
            "icon": "message-circle",
            "visual_theme": "green_particles",
            "hidden": False,
            "important": False,
            "earned": True,
            "earned_at": "2026-07-22T10:00:00+00:00",
            "group_title": "ChatPulse Team",
            "progress": 100,
            "threshold": 100,
            "chain": {"key": "messages", "stage": 2, "total": 8},
            "reward_xp": 10,
            "version": 2,
            "season_key": None,
        },
    }


def test_pending_events_are_scoped_to_verified_telegram_user() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(
        list_pending_events=AsyncMock(return_value=[unlock_event()]),
        get_unlock_event=AsyncMock(return_value=unlock_event()),
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


def test_achievement_card_is_rendered_from_the_verified_users_unlock() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(
        get_unlock_event=AsyncMock(return_value=unlock_event()),
    )

    with TestClient(app) as client:
        app.state.achievement_repository = repository
        response = client.get("/api/miniapp/v1/achievement-events/7/card")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    repository.get_unlock_event.assert_awaited_once_with(101, 7)


def test_event_from_another_user_is_not_acknowledged_or_shared() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(
        list_pending_events=AsyncMock(return_value=[]),
        get_unlock_event=AsyncMock(return_value=None),
        mark_seen=AsyncMock(return_value=False),
        mark_shared=AsyncMock(return_value=False),
    )

    with TestClient(app) as client:
        app.state.achievement_repository = repository
        seen = client.post("/api/miniapp/v1/achievement-events/999/seen")
        card = client.get("/api/miniapp/v1/achievement-events/999/card")

    assert seen.status_code == 404
    assert seen.json()["detail"] == "Подію досягнення не знайдено."
    assert card.status_code == 404
    assert card.json()["detail"] == "Досягнення для поширення не знайдено."
    repository.mark_seen.assert_awaited_once_with(101, 999)
    repository.get_unlock_event.assert_awaited_once_with(101, 999)
