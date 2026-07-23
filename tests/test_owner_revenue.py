from datetime import UTC, datetime, timedelta

import pytest

from app.billing_models import VipInvoiceIntent, VipPayment, VipTrialClaim
from app.database import Database
from app.models import BotOwner, User, VipGrant
from app.repositories.owner_revenue import OwnerRevenueRepository


@pytest.fixture
async def revenue_repository(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'owner-revenue.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(telegram_id=1, first_name="Owner", username="owner"),
                User(telegram_id=10, first_name="Trial", username="trial"),
                User(telegram_id=20, first_name="Monthly", username="monthly"),
                BotOwner(key="primary", telegram_user_id=1, claimed_at=now),
            ]
        )
        trial_intent = VipInvoiceIntent(
            payload="trial",
            telegram_user_id=10,
            product_code="trial_7d",
            stars_amount=1,
            is_recurring=False,
            status="paid",
            created_at=now - timedelta(days=10),
        )
        monthly_intent = VipInvoiceIntent(
            payload="monthly",
            telegram_user_id=20,
            product_code="monthly_30d",
            stars_amount=59,
            is_recurring=True,
            status="open",
            created_at=now - timedelta(days=2),
        )
        session.add_all([trial_intent, monthly_intent])
        await session.flush()
        trial_payment = VipPayment(
            invoice_intent_id=trial_intent.id,
            telegram_user_id=10,
            product_code="trial_7d",
            stars_amount=1,
            telegram_payment_charge_id="charge-trial",
            status="paid",
            paid_at=now - timedelta(days=10),
            granted_until=now - timedelta(days=3),
        )
        monthly_payment = VipPayment(
            invoice_intent_id=monthly_intent.id,
            telegram_user_id=20,
            product_code="monthly_30d",
            stars_amount=59,
            telegram_payment_charge_id="charge-monthly",
            status="paid",
            is_recurring=True,
            is_first_recurring=True,
            subscription_expiration_date=now + timedelta(days=28),
            paid_at=now - timedelta(days=2),
            granted_until=now + timedelta(days=28),
        )
        session.add_all([trial_payment, monthly_payment])
        await session.flush()
        session.add(
            VipTrialClaim(
                telegram_user_id=10,
                payment_id=trial_payment.id,
                claimed_at=now - timedelta(days=10),
            )
        )
        session.add(
            VipGrant(
                telegram_user_id=20,
                is_active=True,
                starts_at=now - timedelta(days=2),
                expires_at=now + timedelta(days=28),
                granted_by_owner_id=0,
                grant_reason="Telegram Stars · monthly_30d",
            )
        )
    yield OwnerRevenueRepository(database.session_factory), database, now
    await database.dispose()


@pytest.mark.asyncio
async def test_revenue_summary_and_trial_funnel(revenue_repository) -> None:
    repository, _database, now = revenue_repository
    summary = await repository.get_summary(days=30, now=now)

    assert summary["stars"] == 60
    assert summary["payments"] == 2
    assert summary["unique_payers"] == 2
    assert summary["active_subscriptions"] == 1
    assert summary["mrr_stars"] == 59
    assert summary["trial_paid"] == 1
    assert summary["trial_converted"] == 0


@pytest.mark.asyncio
async def test_transactions_support_search_and_notes(revenue_repository) -> None:
    repository, _database, _now = revenue_repository
    payload = await repository.list_transactions(query="monthly", limit=50, offset=0)
    assert payload["total"] == 1
    assert payload["items"][0]["stars_amount"] == 59

    payment_id = payload["items"][0]["id"]
    note = await repository.save_note(
        owner_user_id=1,
        payment_id=payment_id,
        user_id=20,
        text="Перевірена місячна підписка",
    )
    assert note["text"] == "Перевірена місячна підписка"
    detail = await repository.get_transaction(payment_id)
    assert detail["note"]["text"] == "Перевірена місячна підписка"


@pytest.mark.asyncio
async def test_refund_eligibility_blocks_non_latest_or_owner_granted_access(
    revenue_repository,
) -> None:
    repository, database, now = revenue_repository
    transactions = await repository.list_transactions(limit=50, offset=0)
    monthly = next(item for item in transactions["items"] if item["product_code"] == "monthly_30d")
    assert (await repository.refund_eligibility(monthly["id"], now=now))["eligible"] is True

    async with database.session_factory() as session, session.begin():
        grant = await session.get(VipGrant, 20)
        grant.granted_by_owner_id = 1
        grant.grant_reason = "Подарунок власника"

    blocked = await repository.refund_eligibility(monthly["id"], now=now)
    assert blocked["eligible"] is False
    assert "подарований" in blocked["reason"].lower()
