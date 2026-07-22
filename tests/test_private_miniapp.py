from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import InlineKeyboardMarkup, Message

from app.bot.keyboards import private_start_keyboard
from app.bot.routers.private import open_command, private_profile_command


def test_private_start_keyboard_contains_web_app_button() -> None:
    markup = private_start_keyboard(
        "chatpulse_bot",
        "https://chatpulse.example/miniapp",
    )

    assert isinstance(markup, InlineKeyboardMarkup)
    buttons = [button for row in markup.inline_keyboard for button in row]
    web_app = next(button for button in buttons if button.web_app is not None)
    assert web_app.text == "⚡ Відкрити ChatPulse"
    assert web_app.web_app.url == "https://chatpulse.example/miniapp"


@pytest.mark.asyncio
async def test_open_command_sends_miniapp_button() -> None:
    message = SimpleNamespace(answer=AsyncMock())

    await open_command(message, miniapp_url="https://chatpulse.example/miniapp")

    message.answer.assert_awaited_once()
    markup = message.answer.await_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].web_app.url.endswith("/miniapp")


@pytest.mark.asyncio
async def test_private_profile_is_privacy_safe() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=101),
        answer=AsyncMock(),
    )
    repository = SimpleNamespace(
        get_private_summary=AsyncMock(
            return_value={
                "display_name": "Dmytro",
                "global_progress": {
                    "level": 4,
                    "tier": "Бронза",
                    "xp_total": 850,
                    "rank": 2,
                },
                "quick_stats": {
                    "current_streak": 6,
                    "groups_count": 2,
                },
                "groups": [],
                "recent_achievements": [],
            }
        )
    )

    await private_profile_command(
        message,
        miniapp_repository=repository,
        miniapp_url="https://chatpulse.example/miniapp",
    )

    text = message.answer.await_args.args[0]
    assert "рівень 4" in text
    assert "850 XP" in text
    assert "текст" not in text.lower()
