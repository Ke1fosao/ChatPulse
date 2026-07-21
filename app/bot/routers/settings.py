from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards_settings import (
    TIMEZONES,
    reset_confirmation_keyboard,
    settings_keyboard,
)
from app.domain import GroupData
from app.repositories.activity import ActivityRepository

router = Router(name="settings")
GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}
ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
TOGGLE_FIELDS = {
    "is_paused",
    "weekly_reports_enabled",
    "track_messages",
    "track_media",
    "track_replies",
    "track_reactions",
}


def settings_text(settings: dict) -> str:
    status = "призупинено" if settings["is_paused"] else "активний"
    return (
        "⚙️ Налаштування ChatPulse\n\n"
        f"Стан збору: {status}\n"
        f"Часовий пояс: {settings['timezone']}\n"
        f"Щотижневий звіт: {'увімкнено' if settings['weekly_reports_enabled'] else 'вимкнено'}\n"
        "Зміни доступні лише адміністраторам групи."
    )


async def is_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ADMIN_STATUSES


async def ensure_group(
    message: Message,
    repository: ActivityRepository,
    default_timezone: str,
) -> dict:
    settings = await repository.get_group_settings(message.chat.id)
    if settings is not None:
        return settings
    await repository.upsert_group(
        GroupData(
            telegram_chat_id=message.chat.id,
            title=message.chat.title or "Telegram group",
            username=message.chat.username,
            timezone=default_timezone,
        ),
        bot_status="member",
        is_active=True,
    )
    settings = await repository.get_group_settings(message.chat.id)
    assert settings is not None
    return settings


@router.message(Command("settings"), F.chat.type.in_(GROUP_TYPES))
async def settings_command(
    message: Message,
    bot: Bot,
    repository: ActivityRepository,
    default_timezone: str,
) -> None:
    if message.from_user is None or not await is_group_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await message.answer("⚠️ Налаштування доступні лише адміністраторам групи.")
        return
    settings = await ensure_group(message, repository, default_timezone)
    await message.answer(settings_text(settings), reply_markup=settings_keyboard(settings))


@router.message(Command("resetstats"), F.chat.type.in_(GROUP_TYPES))
async def reset_command(message: Message, bot: Bot) -> None:
    if message.from_user is None or not await is_group_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await message.answer("⚠️ Скидати статистику може лише адміністратор.")
        return
    await message.answer(
        "Видалити всю накопичену статистику цієї групи?",
        reply_markup=reset_confirmation_keyboard(),
    )


@router.callback_query(F.data.startswith("settings:"))
async def settings_callback(
    callback: CallbackQuery,
    bot: Bot,
    repository: ActivityRepository,
) -> None:
    message = callback.message
    if message is None:
        return
    if not await is_group_admin(bot, message.chat.id, callback.from_user.id):
        await callback.answer("Лише для адміністраторів", show_alert=True)
        return

    settings = await repository.get_group_settings(message.chat.id)
    if settings is None:
        await callback.answer(
            "Спочатку надішліть звичайне повідомлення в групу", show_alert=True
        )
        return

    parts = callback.data.split(":")
    action = parts[1]
    if action == "toggle" and len(parts) == 3 and parts[2] in TOGGLE_FIELDS:
        field = parts[2]
        settings = await repository.update_group_setting(
            message.chat.id, field, not bool(settings[field])
        )
    elif action == "timezone":
        current = settings["timezone"]
        index = TIMEZONES.index(current) if current in TIMEZONES else 0
        settings = await repository.update_group_setting(
            message.chat.id, "timezone", TIMEZONES[(index + 1) % len(TIMEZONES)]
        )
    elif action == "weekday":
        settings = await repository.update_group_setting(
            message.chat.id,
            "report_weekday",
            (int(settings["report_weekday"]) + 1) % 7,
        )
    elif action == "hour":
        hours = (9, 12, 15, 19, 21)
        current = int(settings["report_hour"])
        index = hours.index(current) if current in hours else 0
        settings = await repository.update_group_setting(
            message.chat.id, "report_hour", hours[(index + 1) % len(hours)]
        )
    elif action == "reset" and len(parts) == 3:
        if parts[2] == "ask":
            await message.edit_text(
                "⚠️ Видалити всю статистику цієї групи? Дію не можна скасувати.",
                reply_markup=reset_confirmation_keyboard(),
            )
            await callback.answer()
            return
        if parts[2] == "confirm":
            await repository.reset_group_stats(message.chat.id)
            settings = await repository.get_group_settings(message.chat.id)
            assert settings is not None
            await message.edit_text(
                "✅ Статистику скинуто. Нові повідомлення почнуть рахуватися одразу.",
                reply_markup=settings_keyboard(settings),
            )
            await callback.answer()
            return
        if parts[2] == "cancel":
            await message.edit_text(
                settings_text(settings), reply_markup=settings_keyboard(settings)
            )
            await callback.answer()
            return

    await message.edit_text(settings_text(settings), reply_markup=settings_keyboard(settings))
    await callback.answer("Збережено")
