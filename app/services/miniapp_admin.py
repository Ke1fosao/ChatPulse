from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import ChatGroup, utc_now

REPORT_THEMES = {"dark_pulse", "telegram_wave", "clean_light"}


async def update_report_theme(
    session_factory: async_sessionmaker[AsyncSession],
    chat_id: int,
    theme: str,
) -> None:
    if theme not in REPORT_THEMES:
        raise ValueError("Unsupported report theme")
    async with session_factory() as session, session.begin():
        group = await session.get(ChatGroup, chat_id)
        if group is None:
            raise LookupError("Group is not registered")
        group.report_card_theme = theme
        group.updated_at = utc_now()
