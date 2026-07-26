# ChatPulse operations runbook

## Ownership and targets

Production owner: the ChatPulse owner account and the operator assigned to the protected `production` GitHub environment.

- Database backup provider: Supabase managed backups.
- Initial RPO: 24 hours for full database loss.
- Initial RTO: 4 hours.
- Telegram Stars payments: reconcile by unique `telegram_payment_charge_id`; successfully recorded payments have a no-loss target.
- Redis is disposable coordination state and is never restored as authoritative data.

## Pre-deployment checklist

1. Confirm PR CI is green on the exact head SHA.
2. Build one image tagged by Git SHA and retain its immutable digest.
3. Record the current Cloud Run revision and image digest.
4. Confirm Supabase backup health and latest successful backup timestamp.
5. Run the dedicated migration job using the same image.
6. Deploy a zero-traffic candidate revision.
7. Verify `/health`, `/ready`, `/openapi.json`, and `/miniapp`.
8. Shift traffic only after smoke checks pass.
9. Observe error rate, latency, webhook failures, scheduler outcomes, database saturation, and Redis failures.

Application instances must never run Alembic on startup.

## Immediate rollback

Rollback immediately when any condition is true:

- readiness fails;
- server errors exceed 2% for 5 minutes;
- p95 latency is more than double baseline for 10 minutes;
- webhook failures/retries continuously increase;
- duplicate scheduler execution occurs;
- payment, XP, or achievement invariants fail;
- a Redis outage makes protected operations unsafe.

Route 100% traffic to the recorded previous revision. Do not automatically downgrade the database. Use a forward-fix migration unless a downgrade was separately tested against a restored database.

## Database incident and restore

1. Freeze destructive owner/billing actions if correctness is uncertain.
2. Record incident start time, current revision, Alembic revision, request IDs, and affected payment charge IDs.
3. Restore the selected Supabase backup into a new isolated project/database, never over the primary database.
4. Set the protected workflow secret `RESTORED_DATABASE_URL` to the restored target.
5. Run `Restore verification` in the protected `restore-verification` environment.
6. Verify critical tables, Alembic revision, row-count queryability, and duplicate Telegram payment charge IDs.
7. Reconcile provider records for payments after the backup timestamp.
8. Promote or migrate data only after owner approval and a written incident plan.

Never upload database dumps, credentials, or customer rows to GitHub artifacts.

## Quarterly restore drill

Record:

- drill date and operator;
- selected backup timestamp;
- restore start/end time;
- achieved RPO/RTO;
- verification workflow result;
- payment reconciliation result;
- issues and owners;
- corrective-action deadline.
