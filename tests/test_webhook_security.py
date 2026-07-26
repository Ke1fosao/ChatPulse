from fastapi.testclient import TestClient

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


def test_scheduler_endpoint_rejects_invalid_secret() -> None:
    settings = build_settings()
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/internal/weekly-reports",
            headers={"X-ChatPulse-Scheduler-Secret": "wrong-secret"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid scheduler secret"}


def test_failed_update_returns_retryable_error_and_second_delivery_succeeds() -> None:
    from unittest.mock import AsyncMock

    settings = build_settings()
    app = create_app(settings)
    headers = {"X-Telegram-Bot-Api-Secret-Token": settings.webhook_header_secret}
    payload = {"update_id": 77}
    with TestClient(app, raise_server_exceptions=False) as client:
        dispatcher = app.state.dispatcher
        dispatcher.feed_update = AsyncMock(side_effect=[RuntimeError("boom"), None])
        failed = client.post(settings.webhook_path, headers=headers, json=payload)
        retried = client.post(settings.webhook_path, headers=headers, json=payload)
        duplicate = client.post(settings.webhook_path, headers=headers, json=payload)
    assert failed.status_code == 500
    assert retried.status_code == 200
    assert retried.json() == {"ok": True}
    assert duplicate.status_code == 200
    assert duplicate.json() == {"ok": True, "duplicate": True}
    assert dispatcher.feed_update.await_count == 2
