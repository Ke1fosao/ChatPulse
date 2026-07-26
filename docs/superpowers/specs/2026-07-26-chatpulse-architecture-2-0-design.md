# ChatPulse Architecture 2.0 Design

## Status

Approved for implementation as the second ChatPulse hardening stage after Stability 1.0.

## Goal

Make ChatPulse easier to change, safe under concurrent Telegram traffic, faster when loading group access state, and resilient when one frontend data source fails.

This stage does not add new user-facing product features. Existing URLs, visual behavior, achievements, VIP rules, group statistics, and Telegram commands remain functionally equivalent unless an endpoint is explicitly listed as legacy below.

## Current Problems

1. `app/api/miniapp/routes.py` contains unrelated home, profile, achievement, group, settings, reset, and image endpoints in one module.
2. The codebase has overlapping group APIs: the current Groups 2.0 endpoints and obsolete dashboard/ranking endpoints.
3. Group lists perform Telegram membership, admin, and bot-status requests sequentially for every group.
4. Telegram access failures are converted directly to `False`, causing temporary Telegram outages to look like lost permissions.
5. Group settings and reset operations use several independent repository transactions, allowing partially applied state.
6. XP caps, levels, streaks, achievements, and daily counters are read and changed without database row locking.
7. Large repositories combine writes, queries, serialization, and unrelated domains.
8. JSON API endpoints return unvalidated dictionaries without explicit FastAPI response models.
9. The Mini App bootstrap uses one `Promise.all`; one optional request failure prevents the entire application from opening.

## Scope

### 1. Canonical Mini App API

Keep the public prefix `/api/miniapp/v1` to avoid unnecessary client migration.

Split API handlers into focused modules:

- `app/api/miniapp/home.py`
- `app/api/miniapp/profile.py`
- `app/api/miniapp/achievements.py`
- `app/api/miniapp/groups.py`
- `app/api/miniapp/group_settings.py`
- `app/api/miniapp/access.py`

Remove these legacy endpoints and their unused TypeScript client methods:

- `GET /api/miniapp/v1/groups`
- `GET /api/miniapp/v1/groups/{chat_id}`
- `GET /api/miniapp/v1/groups/{chat_id}/rankings`
- `GET /api/miniapp/v1/profile-card`

Retain the current canonical endpoints:

- `GET /groups-v2`
- `GET /groups/{chat_id}/overview`
- `GET /groups/{chat_id}/ranking`
- `GET /groups/{chat_id}/analytics`
- `GET /groups/{chat_id}/awards`
- group favorite, pause, resume, report, settings, reset, weekly card
- home, onboarding, levels, achievements, achievement events, showcase profile card

A regression test must prove that frontend source code contains no reference to removed paths and that those paths return `404`.

### 2. Telegram Access Cache

Add `TelegramAccessCache` behind `TelegramAccessService`.

Cache keys:

- member/admin: `(chat_id, user_id)`
- bot status: `(chat_id, bot_id)`

Cache values store the raw normalized Telegram member status, not only booleans.

TTL policy:

- positive member/admin status: 60 seconds
- negative member status: 15 seconds
- bot status: 30 seconds
- stale grace period after a Telegram API failure: 300 seconds
- maximum entries: 10,000 with least-recently-used eviction

Concurrent misses for the same key must be coalesced into one Telegram request. Group-list checks must run concurrently with a limit of 8 Telegram requests.

Owners continue to bypass Telegram admin checks. Explicit invalidation methods must exist for one user, one group, and the whole cache.

Temporary Telegram failures use a non-expired stale value when available. Without any cached value, the service remains fail-closed.

### 3. Transaction Boundaries

Introduce application services that own multi-repository operations:

- `GroupSettingsService.update_settings(...)`
- `GroupSettingsService.reset_group(...)`
- `ActivityWriteService.record_message(...)`
- `ActivityWriteService.record_reaction(...)`

Each operation uses one `AsyncSession` and one transaction. Repository internals accept a caller-owned session; public compatibility wrappers may still open a transaction for single operations.

A failure in any sub-step must roll back every changed table.

### 4. XP Concurrency Protection

Before calculating or changing XP, lock the relevant rows in a deterministic order:

1. `ChatGroup`
2. `User`
3. `GroupMember`
4. `MessageAuthor`
5. `DailyActivity`
6. `GlobalDailyXP`
7. streak-protection rows

PostgreSQL uses `SELECT ... FOR UPDATE`. Missing daily rows are created through conflict-safe inserts, then selected and locked.

SQLite tests use the same repository API and an in-process keyed async lock, because SQLite does not provide equivalent row locks. The keyed lock is a local safety layer; PostgreSQL row locks remain the cross-instance source of truth.

Required invariants:

- one Telegram message can receive XP at most once;
- group daily XP never exceeds 200;
- global daily XP never exceeds 400;
- parallel awards do not lose increments;
- levels match final XP totals;
- an achievement unlock is inserted at most once;
- streak advancement occurs at most once per active date.

### 5. Repository Decomposition

Replace oversized mixed-responsibility modules with packages while preserving stable facade imports.

`app/repositories/activity/`:

- `repository.py` — facade
- `writes.py` — message and reaction writes
- `queries.py` — summaries, rankings, period reads
- `settings.py` — group configuration and reset primitives
- `shared.py` — serializers and internal helpers

`app/repositories/miniapp/`:

- `repository.py` — facade
- `home.py` — home/profile queries
- `groups.py` — group dashboard and list queries
- `achievements.py` — achievement reads
- `analytics.py` — premium/year analytics currently in `miniapp_v2.py`
- `shared.py` — membership, summaries, serialization helpers

Delete `app/repositories/miniapp_v2.py` after its behavior is integrated into the canonical package. Existing imports `from app.repositories.activity import ActivityRepository` and `from app.repositories.miniapp import MiniAppRepository` remain valid.

No repository file created in this stage may exceed 350 lines unless it is a generated migration or a static catalog.

### 6. Typed API Responses

Define Pydantic v2 response models under `app/api/miniapp/responses/`.

Rules:

- `ConfigDict(extra="forbid")` for API payload models;
- explicit models for home, account access, group cards, overview, ranking, analytics, awards, achievements, settings, onboarding, and simple `{ok: true}` responses;
- all JSON Mini App routes declare `response_model`;
- binary image routes remain `Response` and are excluded from JSON modeling;
- repository dictionaries are validated at the service/API boundary before response serialization;
- OpenAPI tests verify that canonical endpoints reference schemas instead of anonymous untyped objects.

### 7. Independent Frontend Bootstrap

Replace the all-or-nothing bootstrap with independent resources:

- critical: home/account shell
- optional: onboarding
- optional: groups
- optional: achievements

Each resource has `idle | loading | success | error`, data, error, and retry behavior. Initial loading uses `Promise.allSettled` or equivalent independent requests.

Rules:

- home failure shows the full-screen retry state;
- groups failure leaves home/profile usable and shows a local retry state on Groups;
- achievements failure leaves navigation usable and shows a local retry state on Achievements;
- onboarding failure does not block an existing user from entering the app;
- account-blocked errors always take priority and cancel remaining requests;
- requests use `AbortController` and ignore stale completions after reload or unmount;
- retrying one resource does not refetch successful unrelated resources;
- Telegram initialization runs once.

## Error Handling

- API validation errors preserve existing Ukrainian user-facing messages.
- Telegram cache failures are logged with operation, chat ID, user ID where applicable, and whether stale data was used; no bot token or init data is logged.
- Transaction services translate expected missing-record conditions to existing `404` or `403` API behavior.
- Unexpected database errors roll back and propagate to the existing FastAPI error handling.
- Cache invalidation failure cannot break the primary database operation.

## Observability

Add structured log events:

- `telegram_access_cache_hit`
- `telegram_access_cache_miss`
- `telegram_access_cache_stale`
- `telegram_access_cache_evicted`
- `transaction_rolled_back`
- `xp_lock_wait_ms`
- `miniapp_resource_failed`

Do not log sensitive Telegram payloads.

## Testing

### Backend

- cache TTL, negative TTL, stale fallback, LRU eviction, request coalescing, invalidation;
- bounded concurrent group access checks;
- atomic settings update rollback;
- atomic reset rollback;
- parallel message and reaction XP awards;
- XP cap and level invariants;
- duplicate achievement and streak prevention;
- removed endpoint `404` tests;
- response-model validation and OpenAPI schema tests;
- facade import compatibility tests;
- complete existing pytest suite.

### Frontend

- partial bootstrap failure keeps unaffected screens available;
- blocked account wins over parallel resource success;
- one-resource retry does not reload others;
- stale/aborted requests cannot overwrite newer state;
- removed API methods and paths are absent;
- complete Vitest, typecheck, Vite build, and WebKit route tests.

### Production

- deterministic dependency install;
- Alembic upgrade remains successful;
- production Docker image builds;
- readiness behavior remains unchanged.

## Delivery

Implementation is developed in `architecture/chatpulse-2-0` through a draft pull request. It may be merged into `main` only when frontend, backend, WebKit, migration, and Docker jobs are all green on the exact PR head.