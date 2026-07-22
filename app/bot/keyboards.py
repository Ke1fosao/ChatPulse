from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


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


def open_miniapp_keyboard(miniapp_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡ Відкрити ChatPulse",
                    web_app=WebAppInfo(url=miniapp_url),
                )
            ]
        ]
    )


def private_start_keyboard(
    bot_username: str,
    miniapp_url: str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if miniapp_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="⚡ Відкрити ChatPulse",
                    web_app=WebAppInfo(url=miniapp_url),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="➕ Додати ChatPulse до групи",
                url=f"https://t.me/{bot_username}?startgroup=true",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
