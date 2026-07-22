from app.services.report_cards import THEMES, render_weekly_report_card


def payload() -> dict:
    return {
        "group_title": "ChatPulse Test",
        "summary": {
            "messages_count": 125,
            "reactions_received": 42,
            "active_members": 7,
            "media_count": 13,
        },
        "nominations": ["🏆 Балакун тижня: Дмитро — 50"],
        "comparison_line": "🔥 Група стала активнішою: +20%",
        "top_message": {"display_name": "Віка", "reactions_count": 12},
        "achievements": [{"display_name": "Дмитро", "title": "Перші кроки"}],
    }


def test_all_report_themes_render_png() -> None:
    for theme in THEMES:
        image = render_weekly_report_card(payload(), theme)
        assert image.startswith(b"\x89PNG")
        assert len(image) > 10_000
