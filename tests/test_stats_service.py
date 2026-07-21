from app.services.stats import format_group_stats, format_member_stats, format_top_members


def test_group_stats_formats_summary() -> None:
    text = format_group_stats(
        {
            "messages_count": 12,
            "media_count": 3,
            "replies_count": 5,
            "active_members": 4,
        }
    )

    assert text == (
        "📊 Статистика групи\n\n"
        "💬 Повідомлень: 12\n"
        "🖼 Медіа: 3\n"
        "↩️ Відповідей: 5\n"
        "👥 Активних учасників: 4"
    )


def test_group_stats_handles_empty_group() -> None:
    assert (
        format_group_stats(
            {
                "messages_count": 0,
                "media_count": 0,
                "replies_count": 0,
                "active_members": 0,
            }
        )
        == "📊 Поки що статистики немає. Напишіть перші повідомлення в групі."
    )


def test_top_members_formats_ranked_list() -> None:
    text = format_top_members(
        [
            {
                "telegram_user_id": 1,
                "display_name": "Dmytro",
                "username": "dmytro",
                "messages_count": 12,
                "media_count": 2,
                "replies_count": 3,
            },
            {
                "telegram_user_id": 2,
                "display_name": "Vika",
                "username": None,
                "messages_count": 7,
                "media_count": 1,
                "replies_count": 5,
            },
        ]
    )

    assert text == ("🏆 Топ учасників\n\n🥇 Dmytro — 12 повідомлень\n🥈 Vika — 7 повідомлень")


def test_member_stats_formats_profile_and_empty_state() -> None:
    assert format_member_stats(None) == "👤 Для вас ще немає статистики в цій групі."
    assert format_member_stats(
        {
            "telegram_user_id": 1,
            "display_name": "Dmytro",
            "username": "dmytro",
            "messages_count": 1,
            "media_count": 0,
            "replies_count": 0,
        }
    ) == ("👤 Dmytro\n\n💬 Повідомлень: 1\n🖼 Медіа: 0\n↩️ Відповідей: 0")
