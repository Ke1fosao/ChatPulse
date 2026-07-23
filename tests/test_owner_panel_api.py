from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.miniapp.dependencies import get_miniapp_user
from app.config import Settings
from app.main import create_app
from app.services.admin_access import AdminActor, ROLE_PERMISSIONS


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


def owner_actor() -> AdminActor:
    return AdminActor(
        telegram_user_id=101,
        role="owner",
        permissions=ROLE_PERMISSIONS["owner"],
    )


def test_non_staff_cannot_open_owner_session() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user

    with TestClient(app) as client:
        app.state.user_control_repository = SimpleNamespace(
            resolve_actor=AsyncMock(return_value=None)
        )
        response = client.get("/api/owner/v1/session")

    assert response.status_code == 403


def test_owner_can_read_overview_and_filtered_users() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    actor = owner_actor()
    panel = SimpleNamespace(
        get_overview=AsyncMock(
            return_value={
                "users_total": 12,
                "groups_total": 3,
                "active_groups": 2,
                "vip_total": 1,
                "messages_7d": 450,
            }
        )
    )
    users = SimpleNamespace(
        resolve_actor=AsyncMock(return_value=actor),
        list_users=AsyncMock(
            return_value={"items": [], "total": 0, "limit": 25, "offset": 0}
        ),
    )

    with TestClient(app) as client:
        app.state.owner_repository = SimpleNamespace(is_owner=AsyncMock(return_value=True))
        app.state.owner_panel_repository = panel
        app.state.user_control_repository = users
        overview = client.get("/api/owner/v1/overview")
        response = client.get(
            "/api/owner/v1/users?q=dmytro&vip=active&account_status=blocked"
            "&role=moderator&payment=paid&sort=xp_desc&limit=25&offset=0"
        )

    assert overview.status_code == 200
    assert overview.json()["users_total"] == 12
    assert response.status_code == 200
    users.list_users.assert_awaited_once()
    call = users.list_users.await_args
    assert call.args[0] == actor
    assert call.kwargs["query"] == "dmytro"
    assert call.kwargs["vip_filter"] == "active"
    assert call.kwargs["status_filter"] == "blocked"
    assert call.kwargs["role_filter"] == "moderator"
    assert call.kwargs["payment_filter"] == "paid"
    assert call.kwargs["sort"] == "xp_desc"
    assert call.kwargs["limit"] == 25


def test_owner_can_grant_permanent_vip_only_with_explicit_confirmation() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    actor = owner_actor()
    user_repository = SimpleNamespace(resolve_actor=AsyncMock(return_value=actor))
    service = SimpleNamespace(
        grant=AsyncMock(
            return_value={
                "telegram_user_id": 202,
                "is_active": True,
                "starts_at": "2026-07-22T10:00:00+00:00",
                "expires_at": None,
            }
        )
    )

    with TestClient(app) as client, patch(
        "app.api.owner.routes._vip_service",
        return_value=service,
    ):
        app.state.user_control_repository = user_repository
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
    service.grant.assert_awaited_once_with(
        actor,
        202,
        expires_at=None,
        reason="VIP клієнт",
    )


def test_owner_cannot_grant_vip_to_self() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    actor = owner_actor()
    service = SimpleNamespace(
        grant=AsyncMock(
            side_effect=ValueError("Власника ChatPulse не можна змінювати цією дією.")
        )
    )

    with TestClient(app) as client, patch(
        "app.api.owner.routes._vip_service",
        return_value=service,
    ):
        app.state.user_control_repository = SimpleNamespace(
            resolve_actor=AsyncMock(return_value=actor)
        )
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
    actor = owner_actor()
    service = SimpleNamespace(
        revoke=AsyncMock(return_value={"telegram_user_id": 202, "is_active": False})
    )

    with TestClient(app) as client, patch(
        "app.api.owner.routes._vip_service",
        return_value=service,
    ):
        app.state.user_control_repository = SimpleNamespace(
            resolve_actor=AsyncMock(return_value=actor)
        )
        response = client.request(
            "DELETE",
            "/api/owner/v1/users/202/vip",
            json={
                "reason": "VIP завершено",
                "confirmation": "ВІДКЛИКАТИ VIP",
            },
        )

    assert response.status_code == 200
    service.revoke.assert_awaited_once_with(actor, 202, reason="VIP завершено")
