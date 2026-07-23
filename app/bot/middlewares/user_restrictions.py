from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.repositories.user_control import UserControlRepository


class BlockedUserMiddleware(BaseMiddleware):
    def __init__(self, repository: UserControlRepository) -> None:
        self._repository = repository

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_user = getattr(event, "from_user", None) or getattr(event, "user", None)
        if telegram_user is None:
            return await handler(event, data)

        user_id = int(telegram_user.id)
        if not await self._repository.is_blocked(user_id):
            return await handler(event, data)

        chat = getattr(event, "chat", None)
        if chat is None and isinstance(event, CallbackQuery) and event.message is not None:
            chat = event.message.chat
        source = "bot_private" if chat is not None and chat.type == "private" else "bot_group"
        await self._repository.record_blocked_access(user_id, source)

        if source == "bot_private":
            message = "Доступ до ChatPulse обмежено адміністратором."
            if isinstance(event, CallbackQuery):
                await event.answer(message, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(message)
        return None
