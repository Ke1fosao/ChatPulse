from app.models import ChatGroup, utc_now
from app.repositories.gamification import GamificationRepository

REPORT_THEMES = {"dark_pulse", "telegram_wave", "clean_light"}


class MiniAppGamificationRepository(GamificationRepository):
    async def update_report_theme(self, chat_id: int, theme: str) -> None:
        if theme not in REPORT_THEMES:
            raise ValueError("Unsupported report theme")
        async with self._session_factory() as session, session.begin():
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                raise LookupError("Group is not registered")
            group.report_card_theme = theme
            group.updated_at = utc_now()
