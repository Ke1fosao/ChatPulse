from functools import lru_cache

from pydantic import Field
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

    redis_url: str | None = None
    redis_required: bool = False
    redis_key_prefix: str = Field(default="chatpulse:v1", min_length=1, max_length=64)
    redis_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    redis_socket_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    redis_max_connections: int = Field(default=20, ge=1, le=200)

    @property
    def webhook_path(self) -> str:
        return f"/telegram/webhook/{self.webhook_path_secret}"

    @property
    def webhook_url(self) -> str | None:
        if not self.webhook_base_url:
            return None
        return f"{self.webhook_base_url.rstrip('/')}{self.webhook_path}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
