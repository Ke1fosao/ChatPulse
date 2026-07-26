from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(min_length=1)
    webhook_base_url: str | None = None
    webhook_path_secret: str = Field(min_length=8)
    webhook_header_secret: str = Field(min_length=8)
    scheduler_secret: str | None = Field(default=None, min_length=8)
    database_url: str = "sqlite+aiosqlite:///./chatpulse.db"
    default_timezone: str = "Europe/Kyiv"
    owner_telegram_id: int | None = Field(default=None, gt=0)

    environment: str = Field(default="development", min_length=1, max_length=32)
    build_sha: str = Field(default="unknown", min_length=1, max_length=128)
    cloud_run_revision: str | None = Field(default=None, max_length=128)
    trust_proxy_headers: bool = False

    redis_url: str | None = None
    redis_required: bool = False
    redis_key_prefix: str = Field(default="chatpulse:v1", min_length=1, max_length=64)
    redis_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    redis_socket_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    redis_max_connections: int = Field(default=20, ge=1, le=200)

    webhook_max_body_bytes: int = Field(default=524_288, ge=1024, le=524_288)
    webhook_max_concurrency: int = Field(default=20, ge=1, le=100)

    metrics_enabled: bool = False
    internal_metrics_token: str | None = Field(default=None, min_length=16)

    sentry_dsn: str | None = None
    sentry_environment: str | None = None
    sentry_traces_sample_rate: float = Field(default=0.05, ge=0, le=1)

    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=5, ge=0, le=100)
    db_pool_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86_400)
    db_statement_timeout_ms: int = Field(default=15_000, ge=100, le=300_000)
    db_slow_query_ms: int = Field(default=500, ge=10, le=60_000)
    db_disable_prepared_statements: bool = False

    @model_validator(mode="after")
    def validate_operational_contracts(self) -> "Settings":
        if any(character.isspace() for character in self.redis_key_prefix):
            raise ValueError("REDIS_KEY_PREFIX must not contain whitespace")
        if self.metrics_enabled and not self.internal_metrics_token:
            raise ValueError("INTERNAL_METRICS_TOKEN is required when metrics are enabled")
        if self.production:
            if not self.redis_required:
                raise ValueError("REDIS_REQUIRED must be true in production")
            if not self.redis_url:
                raise ValueError("REDIS_URL is required in production")
            if not self.redis_url.casefold().startswith("rediss://"):
                raise ValueError("Production Redis must use TLS via rediss://")
        return self

    @property
    def webhook_path(self) -> str:
        return f"/telegram/webhook/{self.webhook_path_secret}"

    @property
    def webhook_url(self) -> str | None:
        if not self.webhook_base_url:
            return None
        return f"{self.webhook_base_url.rstrip('/')}{self.webhook_path}"

    @property
    def production(self) -> bool:
        return self.environment.casefold() in {"production", "prod"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
