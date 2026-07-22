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
        auth_date="2026-07-22T10:00:00Z",
    )


def test_admin_can_update_exact_report_time_and_theme() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    access = SimpleNamespace(check_admin=AsyncMock(return_value=True))
    repository = SimpleNamespace(
        update_group_setting=AsyncMock(),
        get_group_settings=AsyncMock(
            return_value={
                "telegram_chat_id": -1001,
                "is_paused": True,
                "weekly_reports_enabled": True,
                "timezone": "Europe/Kyiv",
                "report_weekday": 6,
                "report_hour": 0,
                "report_minute": 15,
                "track_messages": True,
                "track_media": True,
                "track_replies": True,
                "track_reactions": True,
            }
        ),
    )
    gamification = SimpleNamespace(
        update_report_time=AsyncMock(),
        get_group_extras=AsyncMock(
            return_value={
                "report_card_theme": "telegram_wave",
                "report_minute": 15,
            }
        ),
    )

    with TestClient(app) as client:
        app.state.telegram_access_service = access
        app.state.repository = repository
        app.state.gamification_repository = gamification
        response = client.patch(
            "/api/miniapp/v1/groups/-1001/settings",
            json={
                "is_paused": True,
                "report_time": "00:15",
                "report_card_theme": "telegram_wave",
            },
        )

    assert response.status_code == 200
    assert response.json()["report_time"] == "00:15"
    gamification.update_report_time.assert_awaited_once_with(-1001, hour=0, minute=15)
    repository.update_group_setting.assert_any_await(
        -1001,
        "report_card_theme",
        "telegram_wave",
    )


def test_non_admin_cannot_update_group_settings() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user

    with TestClient(app) as client:
        app.state.telegram_access_service = SimpleNamespace(
            check_admin=AsyncMock(return_value=False)
        )
        response = client.patch(
            "/api/miniapp/v1/groups/-1001/settings",
            json={"is_paused": True},
        )

    assert response.status_code == 403


def test_reset_requires_explicit_confirmation() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user

    with TestClient(app) as client:
        app.state.telegram_access_service = SimpleNamespace(
            check_admin=AsyncMock(return_value=True)
        )
        invalid = client.post(
            "/api/miniapp/v1/groups/-1001/reset",
            json={"confirmation": "так"},
        )

    assert invalid.status_code == 422
