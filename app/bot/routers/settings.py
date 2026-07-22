from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards_settings import (
    THEME_LABELS,
    TIMEZONES,
    reset_confirmation_keyboard,
    settings_keyboard,
)
from app.domain import GroupData
from app.repositories.activity import ActivityRepository
from app.repositories.gamification import GamificationRepository
from app.services.gamification import parse_report_time

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
    report_time = f"{int(settings['report_hour']):02d}:{int(settings.get('report_minute', 0)):02d}"
    theme = THEME_LABELS.get(
        settings.get("report_card_theme", "dark_pulse"),
        THEME_LABELS["dark_pulse"],
    )
    return (
        "⚙️ Налаштування ChatPulse\n\n"
        f"Стан збору: {status}\n"
        f"Часовий пояс: {settings['timezone']}\n"
        f"Щотижневий звіт: "
        f"{'увімкнено' if settings['weekly_reports_enabled'] else 'вимкнено'}\n"
        f"Час звіту: {report_time}\n"
        f"Тема картки: {theme}\n\n"
        "Точний час можна змінити командою /setreporttime 20:30\n"
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


async def merged_settings(
    chat_id: int,
    repository: ActivityRepository,
    gamification_repository: GamificationRepository,
) -> dict | None:
    settings = await repository.get_group_settings(chat_id)
    if settings is None:
        return None
    settings.update(await gamification_repository.get_group_extras(chat_id))
    return settings


@router.message(Command("settings"), F.chat.type.in_(GROUP_TYPES))
async def settings_command(
    message: Message,
    bot: Bot,
    repository: ActivityRepository,
    gamification_repository: GamificationRepository,
    default_timezone: str,
) -> None:
    if message.from_user is None or not await is_group_admin(
        bot,
        message.chat.id,
        message.from_user.id,
    ):
        await message.answer("⚠️ Налаштування доступні лише адміністраторам групи.")
        return
    await ensure_group(message, repository, default_timezone)
    settings = await merged_settings(message.chat.id, repository, gamification_repository)
    assert settings is not None
    await message.answer(settings_text(settings), reply_markup=settings_keyboard(settings))


@router.message(Command("setreporttime"), F.chat.type.in_(GROUP_TYPES))
async def set_report_time_command(
    message: Message,
    bot: Bot,
    repository: ActivityRepository,
    gamification_repository: GamificationRepository,
    default_timezone: str,
) -> None:
    if message.from_user is None or not await is_group_admin(
        bot,
        message.chat.id,
        message.from_user.id,
    ):
        await message.answer("⚠️ Час звіту може змінювати лише адміністратор.")
        return
    await ensure_group(message, repository, default_timezone)
    raw_value = (message.text or "").partition(" ")[2]
    try:
        parsed = parse_report_time(raw_value)
    except ValueError as exc:
        await message.answer(f"⚠️ {exc}\nПриклад: /setreporttime 20:30")
        return
    await gamification_repository.update_report_time(
        message.chat.id,
        hour=parsed.hour,
        minute=parsed.minute,
    )
    await message.answer(
        f"✅ Щотижневий звіт заплановано на {parsed.hour:02d}:{parsed.minute:02d} "
        "у часовому поясі групи."
    )


@router.message(Command("resetstats"), F.chat.type.in_(GROUP_TYPES))
async def reset_command(message: Message, bot: Bot) -> None:
    if message.from_user is None or not await is_group_admin(
        bot,
        message.chat.id,
        message.from_user.id,
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
    gamification_repository: GamificationRepository,
) -> None:
    message = callback.message
    if message is None:
        return
    if not await is_group_admin(bot, message.chat.id, callback.from_user.id):
        await callback.answer("Лише для адміністраторів", show_alert=True)
        return

    settings = await merged_settings(message.chat.id, repository, gamification_repository)
    if settings is None:
        await callback.answer(
            "Спочатку надішліть звичайне повідомлення в групу",
            show_alert=True,
        )
        return

    parts = callback.data.split(":")
    action = parts[1]
    if action == "toggle" and len(parts) == 3 and parts[2] in TOGGLE_FIELDS:
        field = parts[2]
        await repository.update_group_setting(
            message.chat.id,
            field,
            not bool(settings[field]),
        )
    elif action == "timezone":
        current = settings["timezone"]
        index = TIMEZONES.index(current) if current in TIMEZONES else 0
        await repository.update_group_setting(
            message.chat.id,
            "timezone",
            TIMEZONES[(index + 1) % len(TIMEZONES)],
        )
    elif action == "weekday":
        await repository.update_group_setting(
            message.chat.id,
            "report_weekday",
            (int(settings["report_weekday"]) + 1) % 7,
        )
    elif action == "theme":
        await gamification_repository.cycle_report_theme(message.chat.id)
    elif action == "time_help":
        await callback.answer("Введіть у групі: /setreporttime 20:30", show_alert=True)
        return
    elif action == "reset" and len(parts) == 3:
        if parts[2] == "ask":
            await message.edit_text(
                "⚠️ Видалити всю статистику цієї групи? Дію не можна скасувати.",
                reply_markup=reset_confirmation_keyboard(),
            )
            await callback.answer()
            return
        if parts[2] == "confirm":
            await gamification_repository.reset_group_gamification(message.chat.id)
            await repository.reset_group_stats(message.chat.id)
            settings = await merged_settings(
                message.chat.id,
                repository,
                gamification_repository,
            )
            assert settings is not None
            await message.edit_text(
                "✅ Статистику, XP, серії та досягнення цієї групи скинуто.",
                reply_markup=settings_keyboard(settings),
            )
            await callback.answer()
            return
        if parts[2] == "cancel":
            await message.edit_text(
                settings_text(settings),
                reply_markup=settings_keyboard(settings),
            )
            await callback.answer()
            return

    settings = await merged_settings(message.chat.id, repository, gamification_repository)
    assert settings is not None
    await message.edit_text(settings_text(settings), reply_markup=settings_keyboard(settings))
    await callback.answer("Збережено")
