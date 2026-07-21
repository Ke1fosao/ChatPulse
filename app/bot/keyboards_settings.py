from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд")
TIMEZONES = ("Europe/Kyiv", "Europe/Warsaw", "Europe/Berlin")


def _flag(value: bool) -> str:
    return "✅" if value else "❌"


def settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    paused_label = "▶️ Відновити збір" if settings["is_paused"] else "⏸ Призупинити збір"
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
                    text=f"⏰ {int(settings['report_hour']):02d}:00",
                    callback_data="settings:hour",
                ),
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
