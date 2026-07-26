from app.repositories.miniapp.achievements import MiniAppAchievementsMixin
from app.repositories.miniapp.analytics import MiniAppAnalyticsMixin
from app.repositories.miniapp.groups import MiniAppGroupsMixin
from app.repositories.miniapp.home import MiniAppHomeMixin
from app.repositories.miniapp.shared import MiniAppShared


class MiniAppRepository(
    MiniAppAchievementsMixin,
    MiniAppAnalyticsMixin,
    MiniAppHomeMixin,
    MiniAppGroupsMixin,
    MiniAppShared,
):
    pass
