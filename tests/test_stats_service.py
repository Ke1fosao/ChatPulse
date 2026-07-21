from app.services.nominations import build_nominations, format_weekly_report
from app.services.stats import format_group_stats, format_member_stats, format_top_members

MEMBER = {
    "telegram_user_id": 1,
    "display_name": "Dmytro",
    "username": None,
    "messages_count": 10,
    "media_count": 2,
    "replies_count": 3,
    "reactions_received": 5,
    "photo_count": 2,
    "voice_count": 1,
    "night_messages_count": 4,
    "morning_messages_count": 0,
}


def test_period_formatters_include_reactions() -> None:
    summary = {
        "messages_count": 10,
        "media_count": 2,
        "replies_count": 3,
        "reactions_received": 5,
        "photo_count": 2,
        "voice_count": 1,
        "night_messages_count": 4,
        "morning_messages_count": 0,
        "active_members": 1,
    }
    assert "за 7 днів" in format_group_stats(summary, "week")
    assert "❤️ 5" in format_top_members([MEMBER], "week")
    assert "Отримано реакцій: 5" in format_member_stats(MEMBER, "week")


def test_empty_period_has_clear_message() -> None:
    summary = {
        "messages_count": 0,
        "media_count": 0,
        "replies_count": 0,
        "reactions_received": 0,
        "photo_count": 0,
        "voice_count": 0,
        "night_messages_count": 0,
        "morning_messages_count": 0,
        "active_members": 0,
    }
    assert format_group_stats(summary, "today") == "📊 Статистики сьогодні поки немає."


def test_nominations_and_weekly_report() -> None:
    nominations = build_nominations([MEMBER])
    assert any("Балакун тижня" in item for item in nominations)
    summary = {
        "messages_count": 10,
        "media_count": 2,
        "replies_count": 3,
        "reactions_received": 5,
        "photo_count": 2,
        "voice_count": 1,
        "night_messages_count": 4,
        "morning_messages_count": 0,
        "active_members": 1,
    }
    report = format_weekly_report(summary, [MEMBER], ("❤️", 5))
    assert "Підсумки тижня" in report
    assert "Найпопулярніша реакція: ❤️" in report
