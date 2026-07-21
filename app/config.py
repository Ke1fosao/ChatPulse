from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(min_length=1)
    webhook_base_url: str | None = None
    webhook_path_secret: str = Field(min_length=8)
    webhook_header_secret: str = Field(min_length=8)
    database_url: str = "sqlite+aiosqlite:///./chatpulse.db"
    default_timezone: str = "Europe/Kyiv"

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
