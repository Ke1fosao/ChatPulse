# ChatPulse Stability 1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a production-safe stability release covering webhook retries, migrations, immutable owner identity, CSS isolation, real mobile browser tests, reproducible builds, and readiness checks.

**Architecture:** Keep the existing FastAPI/aiogram/React structure, but add narrow reliability services and release tooling around it. Database state transitions become explicit, deployment runs Alembic before Uvicorn, frontend regressions are tested in WebKit, and release metadata comes from one canonical file.

**Tech Stack:** Python 3.12, FastAPI, aiogram 3, SQLAlchemy async, Alembic, PostgreSQL/SQLite tests, React 19, TypeScript, Vite, Vitest, Playwright WebKit, Docker, GitHub Actions.

## Global Constraints

- Preserve all existing public Mini App and bot behavior unless explicitly changed below.
- Never grant owner access from Telegram username.
- Failed Telegram updates must return a retryable non-2xx response.
- Production schema changes must run through Alembic.
- Four bottom-navigation actions must remain equal-width at 320, 375, 390, and 430 CSS pixels.
- CI must run deterministic installs from committed lock data.
- No merge until frontend, browser, backend, migration, and Docker checks are green.

---

### Task 1: Canonical release version and deterministic installs

**Files:**
- Create: `VERSION`
- Modify: `pyproject.toml`
- Modify: `miniapp/package.json`
- Modify: `miniapp/package-lock.json`
- Modify: `miniapp/vite.config.ts`
- Modify: `app/main.py`
- Modify: `Dockerfile`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/test_health.py`

**Interfaces:**
- Produces: `app.version.APP_VERSION: str` loaded from `VERSION`.
- Produces: Vite define `__CHATPULSE_VERSION__` for frontend release diagnostics.

- [ ] Add a failing test asserting health and cache headers use the canonical version.
- [ ] Add `VERSION` and `app/version.py`.
- [ ] Synchronize package metadata and lockfile root version to the canonical value.
- [ ] Replace every `npm install` in CI/Docker with `npm ci` and copy the lockfile before install.
- [ ] Run backend version tests, frontend typecheck, and Docker build.

### Task 2: Retry-safe Telegram update lifecycle

**Files:**
- Modify: `app/models.py`
- Modify: `app/repositories/activity.py`
- Modify: `app/main.py`
- Test: `tests/test_repository.py`
- Test: `tests/test_webhook.py`

**Interfaces:**
- Produces: `ActivityRepository.begin_update(update_id, update_type, now=None) -> UpdateClaim`.
- Produces: `ActivityRepository.complete_update(update_id, now=None) -> None`.
- Produces: `ActivityRepository.fail_update(update_id, safe_error, now=None) -> None`.

- [ ] Write repository tests for new, completed duplicate, active lease, expired lease, failure, and retry.
- [ ] Write webhook test proving a handler exception returns HTTP 500 and a second delivery is processed.
- [ ] Extend `ProcessedUpdate` with status, attempts, lease timestamps, completion, and safe error fields.
- [ ] Implement atomic claim/update state transitions.
- [ ] Change webhook flow to complete only after successful dispatcher processing and persist failures before re-raising HTTP 500.
- [ ] Run focused repository/webhook tests.

### Task 3: Alembic migration system

**Files:**
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/script.py.mako`
- Create: `migrations/versions/20260726_0001_baseline.py`
- Modify: `pyproject.toml`
- Modify: `app/database.py`
- Modify: `app/main.py`
- Modify: `Dockerfile`
- Test: `tests/test_migrations.py`

**Interfaces:**
- Produces: `Database.ping() -> None`.
- Produces: `alembic upgrade head` as the deployment schema command.

- [ ] Add a migration test that upgrades an empty SQLite database to head and inspects core tables and processed-update columns.
- [ ] Add Alembic dependency and async migration environment importing all model modules.
- [ ] Create a complete baseline migration matching current metadata.
- [ ] Remove unconditional production `create_all` from lifespan; retain explicit test/local helper only.
- [ ] Add a container entrypoint that runs migrations before Uvicorn.
- [ ] Run migration smoke tests and full backend tests.

### Task 4: Immutable owner bootstrap

**Files:**
- Modify: `app/config.py`
- Modify: `.env.example`
- Modify: `app/repositories/owner.py`
- Modify: `app/bot/setup.py` and owner-claim handler files discovered by tests/search
- Test: `tests/test_owner.py`

**Interfaces:**
- Consumes: `Settings.owner_telegram_id: int | None`.
- Produces: owner claim based only on matching numeric Telegram ID.

- [ ] Add tests proving a matching username with a different ID is rejected and the configured ID succeeds regardless of username.
- [ ] Add `OWNER_TELEGRAM_ID` configuration with positive integer validation.
- [ ] Remove `ALLOWED_OWNER_USERNAME` as an authorization source.
- [ ] Pass the configured ID into owner bootstrap/claim flow.
- [ ] Preserve existing claimed owner rows.
- [ ] Run owner and authorization tests.

### Task 5: CSS cleanup and regression guard

**Files:**
- Modify: `miniapp/src/styles/global.css`
- Modify: `miniapp/src/styles/bottom-nav-v2.css`
- Test: `miniapp/src/components/BottomNav.test.tsx` or current navigation test
- Create: `miniapp/src/styles/css-regressions.test.ts`

**Interfaces:**
- Produces: no legacy `.bottom-nav`, `.bottom-nav-item`, or five-column navigation selectors in global CSS.

- [ ] Add a failing test that scans global CSS for forbidden legacy navigation selectors.
- [ ] Remove obsolete bottom-navigation blocks and duplicated overrides from global CSS.
- [ ] Keep only namespaced `cp-bottom-nav*` rules for the live component.
- [ ] Raise navigation label size to a readable mobile minimum without breaking four equal slots.
- [ ] Run navigation unit tests and frontend build.

### Task 6: Playwright WebKit mobile visual checks

**Files:**
- Modify: `miniapp/package.json`
- Modify: `miniapp/package-lock.json`
- Create: `miniapp/playwright.config.ts`
- Create: `miniapp/e2e/fixtures.ts`
- Create: `miniapp/e2e/mobile-layout.spec.ts`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: mocked Telegram WebApp and API fixture usable by all Mini App E2E tests.

- [ ] Add Playwright dependency and deterministic scripts.
- [ ] Create a production-preview WebKit configuration with trace/screenshot on failure.
- [ ] Mock `/api/miniapp/v1/*` with stable fixture payloads and inject Telegram initData.
- [ ] Verify four navigation buttons have approximately equal widths and fill the viewport at 320/375/390/430 px.
- [ ] Add smoke screenshots for home, groups, profile, and owner access gate.
- [ ] Add browser job to CI and upload traces/screenshots on failure.

### Task 7: Truthful readiness endpoint

**Files:**
- Modify: `app/database.py`
- Modify: `app/main.py`
- Test: `tests/test_health.py`

**Interfaces:**
- Produces: `GET /ready` returning 200 `{status: ready}` only when state initialization and `SELECT 1` succeed; otherwise 503 with safe component states.

- [ ] Add tests for ready success and database failure.
- [ ] Implement async `Database.ping()`.
- [ ] Add `/ready` with no raw exception disclosure.
- [ ] Keep `/health` dependency-free.
- [ ] Run focused health tests.

### Task 8: Documentation and complete verification

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `.dockerignore`
- Modify: `.gitignore` if generated Playwright files require it

**Interfaces:**
- Documents migration commands, owner ID configuration, readiness checks, deterministic installs, and browser test commands.

- [ ] Update local and production setup instructions.
- [ ] Run `npm ci`, Vitest, TypeScript, Vite build, Playwright WebKit, Ruff, format check, pytest, compileall, migration upgrade, and Docker build.
- [ ] Open a PR with exact verification evidence.
- [ ] Merge only after all GitHub Actions jobs pass.