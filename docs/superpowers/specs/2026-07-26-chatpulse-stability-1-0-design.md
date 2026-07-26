# ChatPulse Stability 1.0 Design

## Goal

Make ChatPulse safe to change and dependable in production before adding new product features. The release must prevent lost Telegram updates, introduce controlled database migrations, remove mutable-username owner claiming, eliminate legacy CSS collisions, add real browser layout checks, make builds reproducible, and expose a truthful readiness probe.

## Scope

1. Reliable Telegram webhook processing with retry-safe update state.
2. Alembic migrations as the only production schema upgrade mechanism.
3. Owner bootstrap by immutable Telegram user ID from configuration.
4. Removal of obsolete bottom-navigation CSS from the global stylesheet and a guard against reintroducing it.
5. Playwright WebKit smoke and screenshot tests for key Mini App routes and mobile widths.
6. Reproducible Node/Python builds and one application version source.
7. `/ready` endpoint that verifies application startup state and database connectivity.

## Architecture

### Webhook delivery

`processed_updates` becomes a state table rather than a one-time claim table. Each row stores `status`, `attempts`, `last_error`, `started_at`, and `completed_at`. A new repository API returns one of three outcomes: process a new/retryable update, skip a completed duplicate, or skip an update that is already being processed inside a short lease. The webhook marks completion only after `dispatcher.feed_update` succeeds. Failures are recorded and returned as HTTP 500 so Telegram retries.

### Database migrations

Alembic is added to project dependencies. `alembic.ini`, `migrations/env.py`, and an initial baseline migration are committed. Startup no longer calls `Base.metadata.create_all()` in production. Tests and local SQLite may explicitly create schemas, while production runs `alembic upgrade head` before the application process starts. The first migration represents the current full schema and upgrades `processed_updates` with reliability fields.

### Owner identity

`OWNER_TELEGRAM_ID` becomes the authoritative bootstrap identity. `OwnerRepository.claim_owner` accepts only that numeric ID. Username is stored as display metadata but never grants access. Existing `bot_owner` rows remain valid; bootstrap only applies when no owner row exists.

### Frontend isolation and visual verification

Legacy `.bottom-nav` rules are deleted from `global.css`. The live `cp-bottom-nav*` component remains isolated. A static regression test scans bundled CSS for forbidden legacy selectors. Playwright launches the built Mini App with a mocked Telegram SDK and API responses, then verifies that the four bottom-navigation buttons share the viewport evenly on 320, 375, 390, and 430 pixel widths. Screenshots cover home, profile, groups, and owner gate layouts in WebKit.

### Reproducible release

The canonical version lives in `VERSION`. Python and Vite read it during build/runtime. `package.json`, lockfile metadata, API headers, and health responses are synchronized. CI and Docker use `npm ci`; Docker copies `package-lock.json` before installation. Python dependencies use a generated pinned constraints file for production installation while `pyproject.toml` retains compatible ranges for development.

### Health model

`/health` remains a lightweight liveness response. `/ready` performs `SELECT 1`, confirms repositories were initialized, and reports HTTP 503 with a safe component status when the database is unavailable.

## Error handling

- Webhook exceptions are logged with update ID/type, failure state is persisted, and HTTP 500 is returned.
- Duplicate completed updates return HTTP 200 without reprocessing.
- In-flight updates use a finite lease so crashed workers do not block retries forever.
- Migration failures stop container startup.
- Readiness failures never expose credentials or raw database errors.
- Playwright failures upload screenshots and traces in CI.

## Testing

- Repository tests for new, duplicate, failed, leased, and retried updates.
- Webhook integration tests asserting HTTP 500 on handler failure and successful retry.
- Migration smoke test against an empty SQLite database and upgrade-to-head check.
- Owner tests proving username alone cannot claim ownership.
- CSS regression test forbidding old `.bottom-nav` declarations.
- Playwright WebKit layout tests at supported mobile widths.
- Existing frontend, backend, typecheck, production build, compileall, and Docker build remain mandatory.

## Deployment

The container entrypoint runs `alembic upgrade head` and then starts Uvicorn. Cloud Run readiness should target `/ready`; liveness may target `/health`. The PR is merged only after every CI job is green.