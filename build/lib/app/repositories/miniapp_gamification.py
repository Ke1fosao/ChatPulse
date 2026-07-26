from app.models import ChatGroup, utc_now
from app.repositories.gamification import GamificationRepository
from app.services.premium_policy import ALL_REPORT_THEMES, PREMIUM_REPORT_THEMES


class MiniAppGamificationRepository(GamificationRepository):
    async def update_report_theme(
        self,
        chat_id: int,
        theme: str,
        *,
        premium_allowed: bool = False,
    ) -> None:
        if theme not in ALL_REPORT_THEMES:
            raise ValueError("Unsupported report theme")
        if theme in PREMIUM_REPORT_THEMES and not premium_allowed:
            raise PermissionError("Ця тема доступна у ChatPulse VIP.")
        async with self._session_factory() as session, session.begin():
            group = await session.get(ChatGroup, chat_id)
            if group is None:
                raise LookupError("Group is not registered")
            group.report_card_theme = theme
            group.updated_at = utc_now()
