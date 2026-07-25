from types import SimpleNamespace

from app.main import _INDEX_CACHE_HEADERS, APP_VERSION, _miniapp_url


def test_miniapp_url_changes_with_release_version() -> None:
    settings = SimpleNamespace(webhook_base_url="https://chatpulse.example/")

    assert _miniapp_url(settings) == f"https://chatpulse.example/miniapp?v={APP_VERSION}"


def test_miniapp_index_is_never_cached() -> None:
    cache_control = _INDEX_CACHE_HEADERS["Cache-Control"]

    assert "no-store" in cache_control
    assert "no-cache" in cache_control
    assert _INDEX_CACHE_HEADERS["X-ChatPulse-Version"] == APP_VERSION
