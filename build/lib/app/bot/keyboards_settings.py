from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд")
TIMEZONES = ("Europe/Kyiv", "Europe/Warsaw", "Europe/Berlin")
REPORT_THEMES = ("dark_pulse", "telegram_wave", "clean_light")
THEME_LABELS = {
    "dark_pulse": "🌑 Dark Pulse",
    "telegram_wave": "🌊 Telegram Wave",
    "clean_light": "☀️ Clean Light",
}


def _flag(value: bool) -> str:
    return "✅" if value else "❌"


def _back_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="← Назад", callback_data="settings:back")]


def settings_home_keyboard(_settings: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Звіти", callback_data="settings:open:reports")],
            [
                InlineKeyboardButton(
                    text="🧩 Збір даних",
                    callback_data="settings:open:tracking",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎨 Оформлення",
                    callback_data="settings:open:appearance",
                )
            ],
            [InlineKeyboardButton(text="⚡ Стан бота", callback_data="settings:open:status")],
            [
                InlineKeyboardButton(
                    text="🗑 Небезпечні дії",
                    callback_data="settings:open:danger",
                )
            ],
        ]
    )


def reports_keyboard(settings: dict) -> InlineKeyboardMarkup:
    report_time = f"{int(settings['report_hour']):02d}:{int(settings.get('report_minute', 0)):02d}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{_flag(settings['weekly_reports_enabled'])} Щотижневі звіти",
                    callback_data="settings:toggle:weekly_reports_enabled",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📅 {WEEKDAYS[int(settings['report_weekday'])]}",
                    callback_data="settings:weekday",
                ),
                InlineKeyboardButton(
                    text=f"🕒 {settings['timezone']}",
                    callback_data="settings:timezone",
                ),
            ],
            [
                InlineKeyboardButton(text="−30 хв", callback_data="settings:time:-30"),
                InlineKeyboardButton(text=f"⏰ {report_time}", callback_data="settings:noop"),
                InlineKeyboardButton(text="+30 хв", callback_data="settings:time:30"),
            ],
            _back_row(),
        ]
    )


def tracking_keyboard(settings: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{_flag(settings['track_messages'])} Повідомлення",
                    callback_data="settings:toggle:track_messages",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{_flag(settings['track_media'])} Медіа",
                    callback_data="settings:toggle:track_media",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{_flag(settings['track_replies'])} Відповіді",
                    callback_data="settings:toggle:track_replies",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{_flag(settings['track_reactions'])} Реакції",
                    callback_data="settings:toggle:track_reactions",
                )
            ],
            _back_row(),
        ]
    )


def appearance_keyboard(settings: dict) -> InlineKeyboardMarkup:
    theme = settings.get("report_card_theme", "dark_pulse")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=THEME_LABELS.get(theme, THEME_LABELS["dark_pulse"]),
                    callback_data="settings:theme",
                )
            ],
            _back_row(),
        ]
    )


def status_keyboard(settings: dict) -> InlineKeyboardMarkup:
    label = "▶️ Відновити статистику" if settings["is_paused"] else "⏸ Призупинити статистику"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data="settings:toggle:is_paused",
                )
            ],
            _back_row(),
        ]
    )


def danger_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Скинути всю статистику",
                    callback_data="settings:reset:ask",
                )
            ],
            _back_row(),
        ]
    )


def reset_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Так, видалити статистику",
                    callback_data="settings:reset:confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Скасувати",
                    callback_data="settings:reset:cancel",
                )
            ],
        ]
    )


# Compatibility for existing imports and older tests.
settings_keyboard = settings_home_keyboard
