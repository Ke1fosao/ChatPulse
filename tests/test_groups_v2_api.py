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
        webhook_base_url="https://example.com",
    )


def current_user() -> TelegramMiniAppUser:
    return TelegramMiniAppUser(
        telegram_id=101,
        first_name="Dmytro",
        username="dmytro",
        auth_date="2026-07-23T10:00:00Z",
    )


def test_groups_v2_list_and_favorite_contracts() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(
        list_groups=AsyncMock(
            return_value=[
                {
                    "telegram_chat_id": -1001,
                    "title": "Group",
                    "status": {"id": "active"},
                }
            ]
        ),
        set_favorite=AsyncMock(
            return_value={"telegram_chat_id": -1001, "is_favorite": True}
        ),
    )
    access = SimpleNamespace(
        check_admin=AsyncMock(return_value=True),
        check_member=AsyncMock(return_value=True),
    )

    with TestClient(app) as client:
        app.state.groups_v2_repository = repository
        app.state.telegram_access_service = access
        listed = client.get("/api/miniapp/v1/groups-v2")
        favorited = client.put(
            "/api/miniapp/v1/groups/-1001/favorite",
            json={"is_favorite": True},
        )

    assert listed.status_code == 200
    assert listed.json()["groups"][0]["is_admin"] is True
    assert favorited.status_code == 200
    repository.set_favorite.assert_awaited_once_with(101, -1001, True)


def test_split_group_endpoints_return_independent_payloads() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(
        get_overview=AsyncMock(return_value={"group": {"telegram_chat_id": -1001}}),
        get_ranking=AsyncMock(return_value={"rows": [], "metric": "xp", "period": "week"}),
        get_analytics=AsyncMock(return_value={"activity_series": [], "period": "week"}),
        get_awards=AsyncMock(return_value={"nominations": [], "period": "week"}),
    )
    access = SimpleNamespace(
        check_admin=AsyncMock(return_value=True),
        check_member=AsyncMock(return_value=True),
    )

    with TestClient(app) as client:
        app.state.groups_v2_repository = repository
        app.state.telegram_access_service = access
        overview = client.get("/api/miniapp/v1/groups/-1001/overview?period=week")
        ranking = client.get(
            "/api/miniapp/v1/groups/-1001/ranking?period=week&metric=xp"
        )
        analytics = client.get("/api/miniapp/v1/groups/-1001/analytics?period=week")
        awards = client.get("/api/miniapp/v1/groups/-1001/awards?period=week")

    assert overview.status_code == 200
    assert overview.json()["capabilities"]["is_admin"] is True
    assert ranking.status_code == 200
    assert analytics.status_code == 200
    assert awards.status_code == 200


def test_unknown_group_and_non_admin_actions_are_rejected() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(
        get_overview=AsyncMock(return_value=None),
        set_paused=AsyncMock(),
    )
    access = SimpleNamespace(
        check_admin=AsyncMock(return_value=False),
        check_member=AsyncMock(return_value=False),
    )

    with TestClient(app) as client:
        app.state.groups_v2_repository = repository
        app.state.telegram_access_service = access
        missing = client.get("/api/miniapp/v1/groups/-999/overview")
        forbidden = client.post("/api/miniapp/v1/groups/-1001/analytics/pause")

    assert missing.status_code == 404
    assert forbidden.status_code == 403
    repository.set_paused.assert_not_awaited()


def test_admin_can_pause_resume_and_send_report(monkeypatch) -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_miniapp_user] = current_user
    repository = SimpleNamespace(
        set_paused=AsyncMock(
            side_effect=[
                {"telegram_chat_id": -1001, "is_paused": True},
                {"telegram_chat_id": -1001, "is_paused": False},
            ]
        ),
        record_admin_action=AsyncMock(),
    )
    access = SimpleNamespace(check_admin=AsyncMock(return_value=True))
    send_report = AsyncMock(return_value=True)
    monkeypatch.setattr("app.api.miniapp.groups_v2.send_weekly_report", send_report)

    with TestClient(app) as client:
        app.state.groups_v2_repository = repository
        app.state.telegram_access_service = access
        paused = client.post("/api/miniapp/v1/groups/-1001/analytics/pause")
        resumed = client.post("/api/miniapp/v1/groups/-1001/analytics/resume")
        report = client.post("/api/miniapp/v1/groups/-1001/report-now")

    assert paused.json()["is_paused"] is True
    assert resumed.json()["is_paused"] is False
    assert report.status_code == 200
    send_report.assert_awaited_once()
    repository.record_admin_action.assert_awaited_once()
