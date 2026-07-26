import pytest
from pydantic import ValidationError

from app.config import Settings


BASE = {
    "bot_token": "123456:test-token",
    "webhook_path_secret": "path-secret",
    "webhook_header_secret": "header-secret",
}


def test_production_requires_tls_redis_and_required_mode() -> None:
    with pytest.raises(ValidationError, match="REDIS_REQUIRED"):
        Settings(**BASE, environment="production")
    with pytest.raises(ValidationError, match="rediss"):
        Settings(
            **BASE,
            environment="production",
            redis_required=True,
            redis_url="redis://cache.internal",
        )

    configured = Settings(
        **BASE,
        environment="production",
        redis_required=True,
        redis_url="rediss://cache.internal",
    )
    assert configured.production is True


def test_metrics_require_a_strong_token() -> None:
    with pytest.raises(ValidationError, match="INTERNAL_METRICS_TOKEN"):
        Settings(**BASE, metrics_enabled=True)


def test_webhook_body_limit_cannot_exceed_512_kib() -> None:
    with pytest.raises(ValidationError):
        Settings(**BASE, webhook_max_body_bytes=524_289)
