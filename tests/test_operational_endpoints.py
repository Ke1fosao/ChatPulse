from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def settings(**overrides) -> Settings:
    values = {
        "bot_token": "123456:test-token",
        "webhook_path_secret": "path-secret",
        "webhook_header_secret": "header-secret",
        "database_url": "sqlite+aiosqlite:///:memory:",
        "environment": "test",
    }
    values.update(overrides)
    return Settings(**values)


def test_request_id_and_security_headers_are_added() -> None:
    with TestClient(create_app(settings())) as client:
        response = client.get("/health", headers={"X-Request-ID": "request-1234"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-1234"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"


def test_invalid_request_id_is_replaced() -> None:
    with TestClient(create_app(settings())) as client:
        response = client.get("/health", headers={"X-Request-ID": "bad id"})
    assert response.status_code == 200
    assert len(response.headers["X-Request-ID"]) == 32


def test_metrics_endpoint_is_disabled_and_protected() -> None:
    with TestClient(create_app(settings())) as client:
        assert client.get("/internal/metrics").status_code == 404

    configured = settings(
        metrics_enabled=True,
        internal_metrics_token="metrics-token-123456789",
    )
    with TestClient(create_app(configured)) as client:
        assert client.get("/internal/metrics").status_code == 401
        response = client.get(
            "/internal/metrics",
            headers={"Authorization": "Bearer metrics-token-123456789"},
        )
    assert response.status_code == 200
    assert "chatpulse_http_requests_total" in response.text
    assert "chatpulse_rate_limit_total" in response.text
    assert "chatpulse_telegram_api_calls_total" in response.text
    assert "chatpulse_database_checkout_wait_seconds" in response.text


def test_diagnostics_contains_only_safe_build_and_dependency_metadata() -> None:
    configured = settings(
        internal_metrics_token="diagnostics-token-123456",
        build_sha="abc123",
        cloud_run_revision="chatpulse-00042",
    )
    with TestClient(create_app(configured)) as client:
        unauthorized = client.get("/internal/diagnostics")
        response = client.get(
            "/internal/diagnostics",
            headers={"Authorization": "Bearer diagnostics-token-123456"},
        )
    assert unauthorized.status_code == 401
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "0.15.0"
    assert payload["build_sha"] == "abc123"
    assert payload["environment"] == "test"
    assert payload["revision"] == "chatpulse-00042"
    assert payload["migration_revision"] is None
    assert set(payload["dependencies_ms"]) == {"database"}
    assert payload["dependencies_ms"]["database"] >= 0
    assert "sqlite" not in response.text
    assert "test-token" not in response.text


def test_webhook_secret_is_checked_before_oversized_body() -> None:
    configured = settings()
    oversized = b"x" * 524_289
    with TestClient(create_app(configured)) as client:
        forbidden = client.post(
            configured.webhook_path,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
            content=oversized,
        )
        too_large = client.post(
            configured.webhook_path,
            headers={
                "X-Telegram-Bot-Api-Secret-Token": configured.webhook_header_secret,
                "Content-Type": "application/json",
            },
            content=oversized,
        )
    assert forbidden.status_code == 403
    assert too_large.status_code == 413
