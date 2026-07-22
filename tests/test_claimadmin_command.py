from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.routers.private import claim_admin_command
from app.repositories.owner import OwnerClaimResult


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (OwnerClaimResult.CLAIMED, "закріплено як власника"),
        (OwnerClaimResult.ALREADY_OWNER, "вже є власником"),
        (OwnerClaimResult.USERNAME_MISMATCH, "лише акаунту @veheblya"),
        (OwnerClaimResult.CLAIMED_BY_OTHER, "вже закріплений"),
    ],
)
async def test_claimadmin_returns_clear_status(result, expected: str) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=101, username="veheblya"),
        answer=AsyncMock(),
    )
    owner_repository = SimpleNamespace(claim_owner=AsyncMock(return_value=result))

    await claim_admin_command(message, owner_repository)

    owner_repository.claim_owner.assert_awaited_once_with(101, "veheblya")
    text = message.answer.await_args.args[0]
    assert expected in text


@pytest.mark.asyncio
async def test_claimadmin_ignores_update_without_user() -> None:
    message = SimpleNamespace(from_user=None, answer=AsyncMock())
    owner_repository = SimpleNamespace(claim_owner=AsyncMock())

    await claim_admin_command(message, owner_repository)

    owner_repository.claim_owner.assert_not_awaited()
    message.answer.assert_not_awaited()
