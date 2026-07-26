from typing import Any

from aiogram import Bot

from app.repositories.owner import OwnerRepository


class TelegramAccessService:
    def __init__(
        self,
        bot: Bot | Any,
        *,
        owner_repository: OwnerRepository | None = None,
    ) -> None:
        self._bot = bot
        self._owner_repository = owner_repository
        self._bot_id: int | None = None

    async def check_member(self, chat_id: int, user_id: int) -> bool:
        member = await self._safe_get_member(chat_id, user_id)
        if member is None:
            return False
        status = self._status_value(member)
        if status in {"creator", "administrator", "member"}:
            return True
        if status == "restricted":
            return bool(getattr(member, "is_member", False))
        return False

    async def check_admin(self, chat_id: int, user_id: int) -> bool:
        if self._owner_repository is not None and await self._owner_repository.is_owner(user_id):
            return True
        member = await self._safe_get_member(chat_id, user_id)
        if member is None:
            return False
        return self._status_value(member) in {"creator", "administrator"}

    async def get_bot_status(self, chat_id: int) -> str | None:
        bot_id = await self._resolve_bot_id()
        if bot_id is None:
            return None
        member = await self._safe_get_member(chat_id, bot_id)
        if member is None:
            return None
        status = self._status_value(member)
        return status or None

    async def _resolve_bot_id(self) -> int | None:
        if self._bot_id is not None:
            return self._bot_id
        try:
            bot_info = await self._bot.get_me()
        except Exception:
            return None
        resolved = getattr(bot_info, "id", None)
        if resolved is None:
            return None
        self._bot_id = int(resolved)
        return self._bot_id

    async def _safe_get_member(self, chat_id: int, user_id: int) -> Any | None:
        try:
            return await self._bot.get_chat_member(chat_id, user_id)
        except Exception:
            return None

    @staticmethod
    def _status_value(member: Any) -> str:
        status = getattr(member, "status", "")
        value = getattr(status, "value", status)
        return str(value).strip().lower()
