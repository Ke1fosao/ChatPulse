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
        username="veheblya",
        auth_date="2026-07-22T10:00:00Z",
    )


def test_non_owner_cannot_open_owner_session() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user

    with TestClient(app) as client:
        app.state.owner_repository = SimpleNamespace(is_owner=AsyncMock(return_value=False))
        response = client.get("/api/owner/v1/session")

    assert response.status_code == 403


def test_owner_can_read_overview_and_users() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    panel = SimpleNamespace(
        get_overview=AsyncMock(
            return_value={
                "users_total": 12,
                "groups_total": 3,
                "active_groups": 2,
                "vip_total": 1,
                "messages_7d": 450,
            }
        ),
        list_users=AsyncMock(return_value={"items": [], "total": 0}),
    )

    with TestClient(app) as client:
        app.state.owner_repository = SimpleNamespace(is_owner=AsyncMock(return_value=True))
        app.state.owner_panel_repository = panel
        overview = client.get("/api/owner/v1/overview")
        users = client.get("/api/owner/v1/users?q=dmytro&vip=active&limit=25&offset=0")

    assert overview.status_code == 200
    assert overview.json()["users_total"] == 12
    assert users.status_code == 200
    panel.list_users.assert_awaited_once_with(
        query="dmytro",
        vip_filter="active",
        limit=25,
        offset=0,
    )


def test_owner_can_grant_permanent_vip_only_with_explicit_confirmation() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    panel = SimpleNamespace(
        grant_vip=AsyncMock(
            return_value={
                "telegram_user_id": 202,
                "is_active": True,
                "starts_at": "2026-07-22T10:00:00+00:00",
                "expires_at": None,
            }
        )
    )

    with TestClient(app) as client:
        app.state.owner_repository = SimpleNamespace(is_owner=AsyncMock(return_value=True))
        app.state.owner_panel_repository = panel
        invalid = client.post(
            "/api/owner/v1/users/202/vip",
            json={"mode": "permanent", "reason": "VIP клієнт", "confirmation": "так"},
        )
        valid = client.post(
            "/api/owner/v1/users/202/vip",
            json={
                "mode": "permanent",
                "reason": "VIP клієнт",
                "confirmation": "ВИДАТИ VIP",
            },
        )

    assert invalid.status_code == 422
    assert valid.status_code == 200
    panel.grant_vip.assert_awaited_once_with(
        owner_user_id=101,
        target_user_id=202,
        expires_at=None,
        reason="VIP клієнт",
    )


def test_owner_cannot_grant_vip_to_self() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user

    with TestClient(app) as client:
        app.state.owner_repository = SimpleNamespace(is_owner=AsyncMock(return_value=True))
        app.state.owner_panel_repository = SimpleNamespace(grant_vip=AsyncMock())
        response = client.post(
            "/api/owner/v1/users/101/vip",
            json={
                "mode": "permanent",
                "reason": "Неприпустимо",
                "confirmation": "ВИДАТИ VIP",
            },
        )

    assert response.status_code == 400


def test_owner_can_revoke_vip_with_reason_and_confirmation() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    panel = SimpleNamespace(
        revoke_vip=AsyncMock(return_value={"telegram_user_id": 202, "is_active": False})
    )

    with TestClient(app) as client:
        app.state.owner_repository = SimpleNamespace(is_owner=AsyncMock(return_value=True))
        app.state.owner_panel_repository = panel
        response = client.request(
            "DELETE",
            "/api/owner/v1/users/202/vip",
            json={
                "reason": "VIP завершено",
                "confirmation": "ВІДКЛИКАТИ VIP",
            },
        )

    assert response.status_code == 200
    panel.revoke_vip.assert_awaited_once_with(
        owner_user_id=101,
        target_user_id=202,
        reason="VIP завершено",
    )
