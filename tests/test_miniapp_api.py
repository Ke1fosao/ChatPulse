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


def test_home_endpoint_uses_verified_user_identity() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(
        get_home=AsyncMock(return_value={"user": {"telegram_id": 101}, "groups": []})
    )

    with TestClient(app) as client:
        app.state.miniapp_repository = repository
        response = client.get("/api/miniapp/v1/home")

    assert response.status_code == 200
    assert response.json()["user"]["telegram_id"] == 101
    repository.get_home.assert_awaited_once_with(101)


def test_group_endpoint_hides_unknown_or_unauthorized_group() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(get_group_dashboard=AsyncMock(return_value=None))

    with TestClient(app) as client:
        app.state.miniapp_repository = repository
        response = client.get("/api/miniapp/v1/groups/-999?period=week")

    assert response.status_code == 404
    assert response.json()["detail"] == "Групу не знайдено або доступ відсутній."


def test_rankings_endpoint_validates_metric_and_period() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(
        get_rankings=AsyncMock(
            return_value={
                "metric": "xp",
                "period": "month",
                "rows": [],
                "current_user": None,
            }
        )
    )

    with TestClient(app) as client:
        app.state.miniapp_repository = repository
        invalid = client.get("/api/miniapp/v1/groups/-1001/rankings?metric=spam&period=week")
        valid = client.get("/api/miniapp/v1/groups/-1001/rankings?metric=xp&period=month")

    assert invalid.status_code == 422
    assert valid.status_code == 200
    repository.get_rankings.assert_awaited_once_with(101, -1001, "xp", "month")
