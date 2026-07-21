from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.bot.keyboards import add_to_group_keyboard
from app.domain import UserData
from app.repositories.activity import ActivityRepository

router = Router(name="private")


def _user_data(message: Message) -> UserData | None:
    user = message.from_user
    if user is None:
        return None
    return UserData(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
    )


@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def start_command(
    message: Message,
    bot: Bot,
    repository: ActivityRepository,
) -> None:
    user = _user_data(message)
    if user is not None:
        await repository.upsert_user(user)

    bot_info = await bot.get_me()
    await message.answer(
        "👋 Привіт! Я ChatPulse — бот статистики Telegram-груп.\n\n"
        "Додай мене до групи, признач адміністратором, і я почну рахувати "
        "повідомлення, медіа та відповіді без збереження тексту листування.",
        reply_markup=add_to_group_keyboard(bot_info.username),
    )


@router.message(Command("help"), F.chat.type == ChatType.PRIVATE)
async def help_command(message: Message) -> None:
    await message.answer(
        "Як запустити ChatPulse:\n"
        "1. Додай бота до групи.\n"
        "2. Признач його адміністратором.\n"
        "3. Використовуй /stats, /top і /me у групі.\n\n"
        "ChatPulse не зберігає тексти повідомлень або файли."
    )
