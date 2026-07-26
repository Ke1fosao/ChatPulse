from app.repositories.activity.queries import ActivityQueriesMixin
from app.repositories.activity.settings import ActivitySettingsMixin
from app.repositories.activity.shared import ActivityShared
from app.repositories.activity.writes import ActivityWritesMixin


class ActivityRepository(
    ActivitySettingsMixin,
    ActivityWritesMixin,
    ActivityQueriesMixin,
    ActivityShared,
):
    pass
