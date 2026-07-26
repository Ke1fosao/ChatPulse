from dataclasses import dataclass, field
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
    content_length: int = 0
    content_fingerprint: str | None = None
    content_simhash: int | None = None
    has_qualifying_text: bool = False


@dataclass(frozen=True, slots=True)
class AchievementEarned:
    code: str
    title: str
    description: str
    important: bool
    reward_xp: int = 0
    scope: str = "group"


@dataclass(frozen=True, slots=True)
class GamificationUpdate:
    group_xp_awarded: int = 0
    global_xp_awarded: int = 0
    old_group_level: int = 1
    new_group_level: int = 1
    old_global_level: int = 1
    new_global_level: int = 1
    current_streak: int = 0
    achievements: tuple[AchievementEarned, ...] = field(default_factory=tuple)

    @property
    def has_announcement(self) -> bool:
        return (
            self.new_group_level > self.old_group_level
            or self.new_global_level > self.old_global_level
            or any(item.important for item in self.achievements)
        )
