from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain import StatsPeriod

PERIOD_BUTTONS: tuple[tuple[StatsPeriod, str], ...] = (
    ("today", "Сьогодні"),
    ("week", "7 днів"),
    ("month", "Місяць"),
    ("all", "Увесь час"),
)


def period_keyboard(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"{kind}:{period}")]
            for period, label in PERIOD_BUTTONS
        ]
    )
