from app.bot.keyboards_settings import (
    appearance_keyboard,
    danger_keyboard,
    reports_keyboard,
    settings_home_keyboard,
    status_keyboard,
    tracking_keyboard,
)

SETTINGS = {
    "is_paused": False,
    "weekly_reports_enabled": True,
    "timezone": "Europe/Kyiv",
    "report_weekday": 6,
    "report_hour": 19,
    "report_minute": 30,
    "report_card_theme": "dark_pulse",
    "track_messages": True,
    "track_media": True,
    "track_replies": True,
    "track_reactions": True,
}


def _buttons(markup):
    return [button for row in markup.inline_keyboard for button in row]


def test_settings_home_keyboard_has_clear_sections() -> None:
    buttons = _buttons(settings_home_keyboard(SETTINGS))
    labels = [button.text for button in buttons]
    callbacks = [button.callback_data for button in buttons]

    assert labels == [
        "📊 Звіти",
        "🧩 Збір даних",
        "🎨 Оформлення",
        "⚡ Стан бота",
        "🗑 Небезпечні дії",
    ]
    assert callbacks == [
        "settings:open:reports",
        "settings:open:tracking",
        "settings:open:appearance",
        "settings:open:status",
        "settings:open:danger",
    ]


def test_every_settings_section_has_back_button() -> None:
    keyboards = (
        reports_keyboard(SETTINGS),
        tracking_keyboard(SETTINGS),
        appearance_keyboard(SETTINGS),
        status_keyboard(SETTINGS),
        danger_keyboard(),
    )

    for keyboard in keyboards:
        callbacks = [button.callback_data for button in _buttons(keyboard)]
        assert "settings:back" in callbacks


def test_reports_keyboard_exposes_current_schedule_and_time_controls() -> None:
    buttons = _buttons(reports_keyboard(SETTINGS))
    labels = " ".join(button.text for button in buttons)
    callbacks = [button.callback_data for button in buttons]

    assert "19:30" in labels
    assert "Нд" in labels
    assert "Europe/Kyiv" in labels
    assert "settings:time:-30" in callbacks
    assert "settings:time:30" in callbacks


def test_tracking_keyboard_reflects_individual_flags() -> None:
    settings = {**SETTINGS, "track_media": False}
    labels = " ".join(button.text for button in _buttons(tracking_keyboard(settings)))

    assert "✅ Повідомлення" in labels
    assert "❌ Медіа" in labels
    assert "✅ Відповіді" in labels
    assert "✅ Реакції" in labels
