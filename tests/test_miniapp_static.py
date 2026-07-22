from pathlib import Path

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


def test_miniapp_serves_index_and_nested_spa_routes(tmp_path: Path, monkeypatch) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>ChatPulse Mini App</body></html>")
    monkeypatch.setenv("MINIAPP_DIST_DIR", str(dist))

    with TestClient(create_app(build_settings())) as client:
        root = client.get("/miniapp")
        nested = client.get("/miniapp/groups/-1001")

    assert root.status_code == 200
    assert "ChatPulse Mini App" in root.text
    assert nested.status_code == 200
    assert nested.text == root.text


def test_miniapp_serves_assets_and_returns_404_for_missing_hash(
    tmp_path: Path, monkeypatch
) -> None:
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("<html></html>")
    (assets / "app-123.js").write_text("console.log('ChatPulse')")
    monkeypatch.setenv("MINIAPP_DIST_DIR", str(dist))

    with TestClient(create_app(build_settings())) as client:
        asset = client.get("/miniapp/assets/app-123.js")
        missing = client.get("/miniapp/assets/missing.js")

    assert asset.status_code == 200
    assert "ChatPulse" in asset.text
    assert missing.status_code == 404
