# ruff: noqa: F401, F403, F405, F821, I001
from .base import UserControlBase
from .queries import UserQueriesMixin
from .restrictions import UserRestrictionsMixin
from .staff import UserStaffMixin
from .notes_tags import UserNotesTagsMixin
from .xp import UserXpMixin
from .messaging import UserMessagingMixin
from .audit import UserAuditMixin


class UserControlRepository(
    UserQueriesMixin,
    UserRestrictionsMixin,
    UserStaffMixin,
    UserNotesTagsMixin,
    UserXpMixin,
    UserMessagingMixin,
    UserAuditMixin,
    UserControlBase,
):
    pass
