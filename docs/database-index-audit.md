# Production index audit

The 0.15.0 index migration is additive and rollback-safe. It adds only indexes tied to existing hot query shapes.

| Index | Query shape | Reason |
|---|---|---|
| `ix_users_last_activity` | owner search and retention ordering by `last_activity_at` | avoids scanning every user for inactive cohorts |
| `ix_chat_groups_report_due` | active, unpaused groups with weekly reports enabled and matching schedule | scheduler due-group lookup |
| `ix_group_members_user_seen` | groups for one Telegram user ordered or filtered by recent activity | Mini App membership lookup |
| `ix_group_members_chat_xp` | ranking members inside one group by XP | group leaderboard |
| `ix_engagement_notifications_status_claimed` | claimed notification batches awaiting completion | retry-safe lifecycle processing |
| `ix_vip_invoice_status_created` | open invoice intents by age/status | billing cleanup and idempotency |

Existing unique constraints already cover Telegram payment charge reconciliation. Existing indexes cover processed update leases, daily activity, pending achievement events, favorites, audit records, and payment history. No duplicate index is added.

For PostgreSQL staging, capture `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` for each shape before and after the migration. Do not include real parameters or customer data in committed artifacts.
