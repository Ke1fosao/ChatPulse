from app.bot.keyboards_settings import settings_keyboard


def test_settings_keyboard_reflects_flags() -> None:
    markup = settings_keyboard(
        {
            "is_paused": False,
            "weekly_reports_enabled": True,
            "timezone": "Europe/Kyiv",
            "report_weekday": 6,
            "report_hour": 19,
            "track_messages": True,
            "track_media": True,
            "track_replies": True,
            "track_reactions": True,
        }
    )
    text = " ".join(button.text for row in markup.inline_keyboard for button in row)
    assert "Щотижневі звіти" in text
    assert "Europe/Kyiv" in text
    assert "Призупинити збір" in text
