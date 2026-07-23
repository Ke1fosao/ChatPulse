import pytest

from app.database import Database
from app.models import User
from app.repositories.owner import OwnerRepository
from app.services.admin_access import ROLE_PERMISSIONS, resolve_admin_actor
from app.user_control_models import AdminStaff


@pytest.mark.asyncio
async def test_owner_has_every_permission_and_staff_roles_are_fixed(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'admin-access.db'}")
    await database.create_schema()
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(telegram_id=101, username="veheblya", first_name="Owner"),
                User(telegram_id=202, username="admin", first_name="Admin"),
                User(telegram_id=303, username="support", first_name="Support"),
            ]
        )
    await OwnerRepository(database.session_factory).claim_owner(101, "veheblya")
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                AdminStaff(
                    telegram_user_id=202,
                    role="admin",
                    granted_by_owner_id=101,
                ),
                AdminStaff(
                    telegram_user_id=303,
                    role="support",
                    granted_by_owner_id=101,
                ),
            ]
        )

    owner = await resolve_admin_actor(database.session_factory, 101)
    admin = await resolve_admin_actor(database.session_factory, 202)
    support = await resolve_admin_actor(database.session_factory, 303)

    assert owner is not None and owner.role == "owner" and owner.can("staff.manage")
    assert admin is not None and admin.role == "admin" and admin.can("users.block")
    assert admin.can("staff.manage") is False
    assert support is not None and support.permissions == ROLE_PERMISSIONS["support"]
    assert support.can("users.message") is True
    assert support.can("users.block") is False
    await database.dispose()


@pytest.mark.asyncio
async def test_inactive_or_unknown_staff_cannot_resolve(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'admin-access-inactive.db'}")
    await database.create_schema()
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(telegram_id=101, username="veheblya", first_name="Owner"),
                User(telegram_id=202, username="moderator", first_name="Moderator"),
            ]
        )
    await OwnerRepository(database.session_factory).claim_owner(101, "veheblya")
    async with database.session_factory() as session, session.begin():
        session.add(
            AdminStaff(
                telegram_user_id=202,
                role="moderator",
                is_active=False,
                granted_by_owner_id=101,
            )
        )

    assert await resolve_admin_actor(database.session_factory, 202) is None
    assert await resolve_admin_actor(database.session_factory, 999) is None
    await database.dispose()
