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


def settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    paused_label = "▶️ Відновити збір" if settings["is_paused"] else "⏸ Призупинити збір"
    theme = settings.get("report_card_theme", "dark_pulse")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=paused_label, callback_data="settings:toggle:is_paused")],
            [
                InlineKeyboardButton(
                    text=f"{_flag(settings['weekly_reports_enabled'])} Щотижневі звіти",
                    callback_data="settings:toggle:weekly_reports_enabled",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🕒 {settings['timezone']}",
                    callback_data="settings:timezone",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📅 {WEEKDAYS[int(settings['report_weekday'])]}",
                    callback_data="settings:weekday",
                ),
                InlineKeyboardButton(
                    text=(
                        f"⏰ {int(settings['report_hour']):02d}:"
                        f"{int(settings.get('report_minute', 0)):02d}"
                    ),
                    callback_data="settings:time_help",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=THEME_LABELS.get(theme, THEME_LABELS["dark_pulse"]),
                    callback_data="settings:theme",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{_flag(settings['track_messages'])} Повідомлення",
                    callback_data="settings:toggle:track_messages",
                ),
                InlineKeyboardButton(
                    text=f"{_flag(settings['track_media'])} Медіа",
                    callback_data="settings:toggle:track_media",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"{_flag(settings['track_replies'])} Відповіді",
                    callback_data="settings:toggle:track_replies",
                ),
                InlineKeyboardButton(
                    text=f"{_flag(settings['track_reactions'])} Реакції",
                    callback_data="settings:toggle:track_reactions",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Скинути статистику",
                    callback_data="settings:reset:ask",
                )
            ],
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
            [InlineKeyboardButton(text="Скасувати", callback_data="settings:reset:cancel")],
        ]
    )
