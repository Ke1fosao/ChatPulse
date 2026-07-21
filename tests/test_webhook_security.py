from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def build_settings() -> Settings:
    return Settings(
        bot_token="123456:test-token",
        webhook_path_secret="path-secret",
        webhook_header_secret="header-secret",
        database_url="sqlite+aiosqlite:///:memory:",
    )


def test_webhook_rejects_invalid_secret_header() -> None:
    settings = build_settings()
    with TestClient(create_app(settings)) as client:
        response = client.post(
            settings.webhook_path,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
            json={"update_id": 1},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid webhook secret"}
