from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _settings(database_url: str) -> Settings:
    return Settings(
        bot_token="123456:test-token",
        webhook_path_secret="path-secret",
        webhook_header_secret="header-secret",
        database_url=database_url,
    )


def test_ready_reports_database_and_application_state(tmp_path) -> None:
    app = create_app(_settings(f"sqlite+aiosqlite:///{tmp_path / 'ready.db'}"))

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "components": {"application": "ready", "database": "ready"},
    }


def test_health_does_not_depend_on_database_startup() -> None:
    app = create_app(_settings("sqlite+aiosqlite:///./unavailable-parent/health.db"))
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
