from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def add_to_group_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Додати ChatPulse до групи",
                    url=f"https://t.me/{bot_username}?startgroup=true",
                )
            ]
        ]
    )
