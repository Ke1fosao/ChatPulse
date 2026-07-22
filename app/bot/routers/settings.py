from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.keyboards_settings import (
    THEME_LABELS,
    TIMEZONES,
    WEEKDAYS,
    appearance_keyboard,
    danger_keyboard,
    reports_keyboard,
    reset_confirmation_keyboard,
    settings_home_keyboard,
    status_keyboard,
    tracking_keyboard,
)
from app.domain import GroupData
from app.repositories.activity import ActivityRepository
from app.repositories.gamification import GamificationRepository
from app.repositories.owner import OwnerRepository
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
SECTIONS = {"home", "reports", "tracking", "appearance", "status", "danger"}


def _flag(value: bool) -> str:
    return "увімкнено" if value else "вимкнено"


def _report_time(settings: dict) -> str:
    return (
        f"{int(settings['report_hour']):02d}:"
        f"{int(settings.get('report_minute', 0)):02d}"
    )


def settings_text(settings: dict) -> str:
    state = "⏸ Призупинено" if settings["is_paused"] else "🟢 Активний"
    return (
        "⚙️ <b>Керування ChatPulse</b>\n\n"
        f"Стан: <b>{state}</b>\n"
        f"Звіти: <b>{_flag(settings['weekly_reports_enabled'])}</b> · "
        f"{WEEKDAYS[int(settings['report_weekday'])]} {_report_time(settings)}\n"
        f"Часовий пояс: <b>{settings['timezone']}</b>\n\n"
        "Оберіть розділ. Усі зміни застосовуються одразу й це повідомлення "
        "буде оновлюватися без зайвого спаму в групі."
    )


def reports_text(settings: dict) -> str:
    return (
        "📊 <b>Щотижневі звіти</b>\n\n"
        f"Статус: <b>{_flag(settings['weekly_reports_enabled'])}</b>\n"
        f"День: <b>{WEEKDAYS[int(settings['report_weekday'])]}</b>\n"
        f"Час: <b>{_report_time(settings)}</b>\n"
        f"Часовий пояс: <b>{settings['timezone']}</b>\n\n"
        "Натисніть на день або часовий пояс, щоб перейти до наступного "
        "варіанта. Час змінюється кнопками по 30 хвилин."
    )


def tracking_text(settings: dict) -> str:
    return (
        "🧩 <b>Збір даних</b>\n\n"
        f"Повідомлення: <b>{_flag(settings['track_messages'])}</b>\n"
        f"Медіа: <b>{_flag(settings['track_media'])}</b>\n"
        f"Відповіді: <b>{_flag(settings['track_replies'])}</b>\n"
        f"Реакції: <b>{_flag(settings['track_reactions'])}</b>\n\n"
        "ChatPulse не зберігає тексти повідомлень або файли — лише "
        "агреговану статистику."
    )


def appearance_text(settings: dict) -> str:
    theme = THEME_LABELS.get(
        settings.get("report_card_theme", "dark_pulse"),
        THEME_LABELS["dark_pulse"],
    )
    return (
        "🎨 <b>Оформлення звіту</b>\n\n"
        f"Поточна тема: <b>{theme}</b>\n\n"
        "Натисніть кнопку теми, щоб переглянути наступний стиль картки."
    )


def status_text(settings: dict) -> str:
    if settings["is_paused"]:
        detail = "Статистика тимчасово не збирається. Попередні дані збережені."
        state = "⏸ Призупинено"
    else:
        detail = "ChatPulse збирає дозволені типи активності та нараховує XP."
        state = "🟢 Активний"
    return f"⚡ <b>Стан бота</b>\n\nПоточний стан: <b>{state}</b>\n\n{detail}"


def danger_text() -> str:
    return (
        "🗑 <b>Небезпечні дії</b>\n\n"
        "Скидання видалить статистику, XP, серії та досягнення цієї групи. "
        "Цю дію не можна скасувати."
    )


def _screen(section: str, settings: dict) -> tuple[str, InlineKeyboardMarkup]:
    if section == "reports":
        return reports_text(settings), reports_keyboard(settings)
    if section == "tracking":
        return tracking_text(settings), tracking_keyboard(settings)
    if section == "appearance":
        return appearance_text(settings), appearance_keyboard(settings)
    if section == "status":
        return status_text(settings), status_keyboard(settings)
    if section == "danger":
        return danger_text(), danger_keyboard()
    return settings_text(settings), settings_home_keyboard(settings)


def _section_for_action(action: str, field: str | None = None) -> str:
    if action in {"timezone", "weekday", "time"}:
        return "reports"
    if action == "theme":
        return "appearance"
    if action == "toggle":
        if field == "is_paused":
            return "status"
        if field == "weekly_reports_enabled":
            return "reports"
        return "tracking"
    if action == "reset":
        return "danger"
    return "home"


async def is_group_admin(
    bot: Bot,
    chat_id: int,
    user_id: int,
    owner_repository: OwnerRepository | None = None,
) -> bool:
    if owner_repository is not None and await owner_repository.is_owner(user_id):
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except Exception:
        return False
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
    owner_repository: OwnerRepository,
    default_timezone: str,
) -> None:
    if message.from_user is None or not await is_group_admin(
        bot,
        message.chat.id,
        message.from_user.id,
        owner_repository,
    ):
        await message.answer("⚠️ Налаштування доступні лише адміністраторам групи.")
        return
    await ensure_group(message, repository, default_timezone)
    settings = await merged_settings(message.chat.id, repository, gamification_repository)
    assert settings is not None
    text, keyboard = _screen("home", settings)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(Command("setreporttime"), F.chat.type.in_(GROUP_TYPES))
async def set_report_time_command(
    message: Message,
    bot: Bot,
    repository: ActivityRepository,
    gamification_repository: GamificationRepository,
    owner_repository: OwnerRepository,
    default_timezone: str,
) -> None:
    if message.from_user is None or not await is_group_admin(
        bot,
        message.chat.id,
        message.from_user.id,
        owner_repository,
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
async def reset_command(
    message: Message,
    bot: Bot,
    owner_repository: OwnerRepository,
) -> None:
    if message.from_user is None or not await is_group_admin(
        bot,
        message.chat.id,
        message.from_user.id,
        owner_repository,
    ):
        await message.answer("⚠️ Скидати статистику може лише адміністратор.")
        return
    await message.answer(
        "⚠️ Видалити всю статистику цієї групи? Дію не можна скасувати.",
        reply_markup=reset_confirmation_keyboard(),
    )


@router.callback_query(F.data.startswith("settings:"))
async def settings_callback(
    callback: CallbackQuery,
    bot: Bot,
    repository: ActivityRepository,
    gamification_repository: GamificationRepository,
    owner_repository: OwnerRepository,
) -> None:
    message = callback.message
    if message is None:
        return
    if not await is_group_admin(
        bot,
        message.chat.id,
        callback.from_user.id,
        owner_repository,
    ):
        await callback.answer("Лише для адміністраторів групи", show_alert=True)
        return

    settings = await merged_settings(message.chat.id, repository, gamification_repository)
    if settings is None:
        await callback.answer(
            "Спочатку надішліть звичайне повідомлення в групу",
            show_alert=True,
        )
        return

    parts = (callback.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "noop":
        await callback.answer()
        return

    if action == "open" and len(parts) == 3 and parts[2] in SECTIONS:
        section = parts[2]
    elif action == "back":
        section = "home"
    elif action == "toggle" and len(parts) == 3 and parts[2] in TOGGLE_FIELDS:
        field = parts[2]
        await repository.update_group_setting(
            message.chat.id,
            field,
            not bool(settings[field]),
        )
        section = _section_for_action(action, field)
    elif action == "timezone":
        current = settings["timezone"]
        index = TIMEZONES.index(current) if current in TIMEZONES else 0
        await repository.update_group_setting(
            message.chat.id,
            "timezone",
            TIMEZONES[(index + 1) % len(TIMEZONES)],
        )
        section = "reports"
    elif action == "weekday":
        await repository.update_group_setting(
            message.chat.id,
            "report_weekday",
            (int(settings["report_weekday"]) + 1) % 7,
        )
        section = "reports"
    elif action == "time" and len(parts) == 3:
        try:
            delta = int(parts[2])
        except ValueError:
            await callback.answer("Некоректна зміна часу", show_alert=True)
            return
        total = (
            int(settings["report_hour"]) * 60
            + int(settings.get("report_minute", 0))
            + delta
        ) % (24 * 60)
        await gamification_repository.update_report_time(
            message.chat.id,
            hour=total // 60,
            minute=total % 60,
        )
        section = "reports"
    elif action == "theme":
        await gamification_repository.cycle_report_theme(message.chat.id)
        section = "appearance"
    elif action == "reset" and len(parts) == 3:
        reset_action = parts[2]
        if reset_action == "ask":
            await message.edit_text(
                "⚠️ <b>Підтвердження скидання</b>\n\n"
                "Буде видалено статистику, XP, серії та досягнення цієї групи.",
                reply_markup=reset_confirmation_keyboard(),
                parse_mode="HTML",
            )
            await callback.answer()
            return
        if reset_action == "confirm":
            await gamification_repository.reset_group_gamification(message.chat.id)
            await repository.reset_group_stats(message.chat.id)
            settings = await merged_settings(
                message.chat.id,
                repository,
                gamification_repository,
            )
            assert settings is not None
            await message.edit_text(
                "✅ <b>Статистику групи скинуто</b>\n\n"
                "ChatPulse продовжить збір нової активності відповідно до налаштувань.",
                reply_markup=danger_keyboard(),
                parse_mode="HTML",
            )
            await callback.answer("Готово")
            return
        if reset_action == "cancel":
            section = "danger"
        else:
            section = "danger"
    else:
        await callback.answer("Невідома дія", show_alert=True)
        return

    settings = await merged_settings(message.chat.id, repository, gamification_repository)
    assert settings is not None
    text, keyboard = _screen(section, settings)
    await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("Збережено" if action not in {"open", "back"} else None)
