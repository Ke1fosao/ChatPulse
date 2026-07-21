from dataclasses import dataclass
from typing import Literal

StatsPeriod = Literal["today", "week", "month", "all"]


@dataclass(frozen=True, slots=True)
class UserData:
    telegram_id: int
    username: str | None
    first_name: str
    last_name: str | None
    language_code: str | None

    @property
    def display_name(self) -> str:
        name_parts = [self.first_name, self.last_name]
        return " ".join(part for part in name_parts if part).strip() or str(self.telegram_id)


@dataclass(frozen=True, slots=True)
class GroupData:
    telegram_chat_id: int
    title: str
    username: str | None
    timezone: str = "Europe/Kyiv"


@dataclass(frozen=True, slots=True)
class MessageActivity:
    is_media: bool
    is_reply: bool
    is_photo: bool = False
    is_voice: bool = False
