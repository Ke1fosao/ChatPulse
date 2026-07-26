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


def test_openapi_contains_only_canonical_group_paths() -> None:
    paths = create_app(build_settings()).openapi()["paths"]
    assert "/api/miniapp/v1/groups-v2" in paths
    assert "/api/miniapp/v1/groups/{chat_id}/overview" in paths
    assert "/api/miniapp/v1/groups/{chat_id}/ranking" in paths
    assert "/api/miniapp/v1/profile-card-showcase" in paths
    assert "/api/miniapp/v1/groups" not in paths
    assert "/api/miniapp/v1/groups/{chat_id}" not in paths
    assert "/api/miniapp/v1/groups/{chat_id}/rankings" not in paths
    assert "/api/miniapp/v1/profile-card" not in paths
