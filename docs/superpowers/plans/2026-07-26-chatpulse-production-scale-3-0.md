# ChatPulse Production & Scale 3.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ChatPulse safe to operate across multiple Cloud Run instances with shared coordination, abuse protection, production observability, explicit database runtime controls, repeatable load tests, verified recovery procedures, and rollback-safe immutable releases.

**Architecture:** Keep the existing FastAPI/aiogram monolith and PostgreSQL source of truth. Add Redis only as a finite-TTL coordination layer, a policy-driven rate limiter, token-owned distributed leases, bounded-label Prometheus instrumentation, scrubbed optional Sentry integration, explicit SQLAlchemy pool/query controls, and release tooling that separates migrations from application startup. Every production feature degrades according to a written fail-open or fail-closed rule and remains testable without external production services.

**Tech Stack:** Python 3.12, FastAPI, aiogram 3, SQLAlchemy 2 async, Alembic, PostgreSQL/Supabase, Redis 5 asyncio, Prometheus client, Sentry SDK, Locust, React/Vite/Playwright, Docker, GitHub Actions, Google Cloud Run.

## Global Constraints

- Target version is exactly `0.15.0`.
- Base branch is `architecture/chatpulse-2-0`; retarget to `main` only after PR #36 is merged.
- Redis is never the durable source of truth for identity, permissions, billing, XP, achievements, webhook claims, or analytics.
- Every Redis application key uses `REDIS_KEY_PREFIX`, defaults to `chatpulse:v1`, and has a finite TTL.
- Development and tests may run without Redis only when `REDIS_REQUIRED=false`; production documentation requires `true`.
- Protected writes fail closed when their required operational dependency is unavailable; authenticated reads may fail open to authoritative sources.
- Webhook body limit is exactly 512 KiB and webhook concurrency is bounded.
- Metrics labels never contain Telegram IDs, chat IDs, usernames, request IDs, invoice IDs, or raw parameterized URLs.
- Application containers never run database migrations on startup.
- Production migrations are backward-compatible with the previous revision; destructive schema removal is forbidden in this release.
- No secrets, raw Telegram payloads, init data, message text, payment payloads, request bodies, or private notes may enter logs, metrics, Sentry, artifacts, or load-test reports.
- CI is read-only and may not create implementation commits.
- Existing Architecture 2.0 regression tests remain green.

---

### Task 1: Normalize the Stacked Branch and Freeze Production Contracts

**Files:**
- Modify: `.github/workflows/ci.yml`
- Delete: `architecture-apply.log`
- Delete: `tools/apply_architecture.py` and `tools/architecture-batch.part*` when present
- Create: `tests/test_production_contracts.py`
- Create: `tests/test_artifact_cleanliness.py`

**Interfaces:**
- Produces a read-only CI baseline and regression tests enforcing no self-mutating workflow, no automatic migration in `Dockerfile`, version `0.15.0`, non-root execution, and absence of temporary transport files.

- [ ] Write tests that inspect tracked files and fail when CI has `contents: write`, a workflow invokes `git push`, Docker `CMD` contains `alembic upgrade`, or forbidden temporary files exist.
- [ ] Run `pytest -q tests/test_production_contracts.py tests/test_artifact_cleanliness.py` and verify RED.
- [ ] Replace the inherited self-mutating workflow with read-only jobs; remove temporary implementation transport/log files.
- [ ] Keep release/deploy workflows separate from pull-request CI.
- [ ] Re-run tests and verify GREEN.
- [ ] Commit `chore: normalize production branch contracts`.

### Task 2: Add Redis Runtime and Dependency Lifecycle

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.lock`
- Modify: `app/config.py`
- Create: `app/operations/redis_runtime.py`
- Create: `app/operations/__init__.py`
- Modify: `app/main.py`
- Create: `tests/test_redis_runtime.py`
- Modify: `.env.example`

**Interfaces:**

```python
class RedisRuntime:
    @classmethod
    async def create(cls, settings: Settings) -> RedisRuntime: ...
    @property
    def available(self) -> bool: ...
    async def ping(self) -> float: ...
    async def close(self) -> None: ...
    def key(self, *parts: str | int) -> str: ...
```

`create()` returns a disabled runtime when no URL is configured and Redis is optional, raises startup failure when required, and owns one `redis.asyncio.Redis` connection pool.

- [ ] Write RED tests for optional-disabled, required-missing, successful lifecycle, key prefixing, finite timeout configuration, and startup failure.
- [ ] Add `redis>=5,<6` and configuration fields from the approved design.
- [ ] Implement runtime creation, ping latency, safe close, and scrubbed failure logging.
- [ ] Register runtime in FastAPI lifespan and close it after the bot/database.
- [ ] Verify tests and dependency lock consistency.
- [ ] Commit `feat: add Redis operational runtime`.

### Task 3: Implement Token-Owned Distributed Leases

**Files:**
- Create: `app/operations/leases.py`
- Create: `tests/test_distributed_leases.py`
- Modify: scheduler execution paths in `app/main.py` and lifecycle services

**Interfaces:**

```python
@dataclass(slots=True)
class LeaseHandle:
    name: str
    token: str
    ttl_ms: int
    acquired: bool
    async def renew(self) -> bool: ...
    async def release(self) -> bool: ...

class LeaseService:
    async def acquire(self, name: str, ttl_seconds: int) -> LeaseHandle: ...
```

Acquisition uses `SET NX PX`; renew and release use token-checking Lua scripts. Disabled/unavailable Redis returns a non-acquired handle for singleton jobs.

- [ ] Write RED tests for acquisition, contention, expiry, renewal, foreign-token release, and two service instances.
- [ ] Implement atomic Lua operations and bounded TTL validation.
- [ ] Add operation/time-bucket lease names for weekly reports and VIP/retention lifecycle jobs.
- [ ] Ensure a lost lease stops at the next batch boundary and logs a warning.
- [ ] Verify duplicate execution is zero in a two-instance test.
- [ ] Commit `feat: coordinate singleton jobs with Redis leases`.

### Task 4: Add Atomic Policy-Based Rate Limiting

**Files:**
- Create: `app/operations/rate_limits.py`
- Create: `app/api/rate_limit.py`
- Modify: Mini App, owner, billing, scheduler routers/dependencies
- Create: `tests/test_rate_limits.py`
- Create: `tests/test_rate_limit_policies.py`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int

class RateLimitService:
    async def check(self, policy: str, identity: str) -> RateLimitDecision: ...
```

Use one Redis Lua token bucket. Stable errors are:

```json
{"detail":{"code":"RATE_LIMITED","message":"Забагато запитів. Спробуйте трохи пізніше."}}
```

and dependency failure:

```json
{"detail":{"code":"OPERATIONAL_DEPENDENCY_UNAVAILABLE","message":"Операція тимчасово недоступна."}}
```

- [ ] Write RED tests for refill, burst, atomic concurrent checks, retry time, policy budgets, fail-open reads, fail-closed billing/destructive/scheduler writes, and `Retry-After`.
- [ ] Implement exact approved policies and stable identity hashing without raw sensitive values in keys.
- [ ] Add reusable FastAPI dependencies for read, write, billing, owner-safe, owner-destructive, invalid-auth-IP, and scheduler policies.
- [ ] Wire policies at router boundaries without changing successful response shapes.
- [ ] Verify `429` and `503` behavior.
- [ ] Commit `feat: enforce distributed rate-limit policies`.

### Task 5: Add Webhook Backpressure and Body Protection

**Files:**
- Create: `app/operations/webhook_runtime.py`
- Modify: `app/config.py`
- Modify: `app/main.py`
- Create: `tests/test_webhook_backpressure.py`

**Interfaces:**
- `WebhookRuntime.handle_slot()` is an async context manager recording queue wait and active count.
- Exact maximum body size is 524288 bytes.
- Concurrency default is configurable and bounded between 1 and 100.

- [ ] Write RED tests for oversize rejection before JSON parsing, verified secrets before work, bounded concurrency, queue wait, active decrement after exceptions, duplicate update behavior, and retryable HTTP 500.
- [ ] Implement a semaphore and streaming/body-length guard.
- [ ] Preserve durable update claim semantics from Stability 1.0.
- [ ] Emit webhook metrics/events without raw body logging.
- [ ] Verify repeated concurrency tests.
- [ ] Commit `feat: protect webhook ingestion under burst load`.

### Task 6: Implement Structured Logging, Request IDs, and Redaction

**Files:**
- Create: `app/observability/logging.py`
- Create: `app/observability/request_context.py`
- Create: `app/observability/redaction.py`
- Create: `app/observability/__init__.py`
- Modify: `app/main.py`
- Modify: `app/config.py`
- Create: `tests/test_request_ids.py`
- Create: `tests/test_log_redaction.py`

**Interfaces:**
- Request IDs accept `[A-Za-z0-9._-]{8,128}`; invalid values are replaced with UUID4 hex.
- Responses include `X-Request-ID`.
- `log_event(logger, level, event, **fields)` writes structured records.
- `redact_value()` removes configured secrets, authorization, cookies, init data, webhook payloads, payment payloads, and private notes recursively.

- [ ] Write RED tests for request propagation/generation, JSON production formatter, readable development formatter, context cleanup, nested redaction, secret replacement, and no sensitive traceback extras.
- [ ] Implement contextvars middleware and formatters.
- [ ] Add request completion events with route template, status class, duration, version, environment, and revision.
- [ ] Update webhook logs to use update ID/type only.
- [ ] Verify logs contain no prohibited strings.
- [ ] Commit `feat: add correlated structured logging`.

### Task 7: Add Protected Prometheus Metrics

**Files:**
- Modify: `pyproject.toml`, `requirements.lock`, `app/config.py`
- Create: `app/observability/metrics.py`
- Create: `app/api/internal_metrics.py`
- Modify: operational services to record metrics
- Create: `tests/test_metrics.py`
- Create: `tests/test_metric_cardinality.py`

**Interfaces:**
- `/internal/metrics` exists only when enabled and requires constant-time bearer-token verification.
- Metrics use a dedicated `CollectorRegistry` per app/test instance.
- Route labels use FastAPI route templates or bounded fallback values.

- [ ] Write RED tests for disabled 404, missing/invalid token 401, valid Prometheus text, required counters/histograms/gauges, and forbidden label names/values.
- [ ] Add `prometheus-client>=0.21,<1`.
- [ ] Implement HTTP, webhook, Redis, rate-limit, lease, Telegram, database, rollback, scheduler, and API error metrics.
- [ ] Instrument services without high-cardinality labels.
- [ ] Verify registry isolation and cardinality tests.
- [ ] Commit `feat: expose protected operational metrics`.

### Task 8: Add Scrubbed Optional Sentry Integration

**Files:**
- Modify: `pyproject.toml`, `requirements.lock`, `app/config.py`
- Create: `app/observability/sentry.py`
- Modify: `app/main.py`
- Create: `tests/test_sentry_scrubbing.py`

**Interfaces:**
- `configure_sentry(settings)` is a no-op without DSN.
- `before_send(event, hint)` returns a scrubbed event or `None` for expected validation/rate-limit/permission exceptions.

- [ ] Write RED tests for no-op configuration, trace sample validation, header/cookie/query/body/request-user removal, configured secret scrubbing, and expected 4xx suppression.
- [ ] Add `sentry-sdk[fastapi]>=2,<3`.
- [ ] Implement configuration before app creation and safe event filtering.
- [ ] Verify raw init data and webhook payloads never leave the process.
- [ ] Commit `feat: integrate privacy-safe error tracking`.

### Task 9: Harden Database Runtime and Query Instrumentation

**Files:**
- Modify: `app/config.py`
- Modify: `app/database.py`
- Create: `app/observability/database.py`
- Create: `tests/test_database_runtime.py`
- Create: `tests/test_slow_queries.py`

**Interfaces:**
- PostgreSQL engine receives exact bounded pool settings, `application_name=chatpulse/<version>`, statement timeout, and optional asyncpg statement-cache disablement.
- SQLite receives only local-compatible settings.
- Slow-query events include operation and normalized table names, never SQL parameters.

- [ ] Write RED tests for PostgreSQL and SQLite engine kwargs, invalid bounds, checkout metrics, statement timeout, and scrubbed slow-query normalization.
- [ ] Implement explicit settings and SQLAlchemy event instrumentation.
- [ ] Add connection checkout-wait and query duration metrics.
- [ ] Verify no credentials or parameters appear in events.
- [ ] Commit `perf: harden database runtime configuration`.

### Task 10: Audit and Add High-Traffic Database Indexes

**Files:**
- Create: `migrations/versions/0003_production_indexes.py` using the next actual revision
- Create: `docs/database-index-audit.md`
- Create: `tests/test_production_indexes.py`

**Interfaces:**
- Migration is additive and backward-compatible.
- Every index maps to a real query and has a documented SQLite/PostgreSQL query-plan artifact or fixture assertion.

- [ ] Inventory existing indexes and high-traffic WHERE/ORDER BY patterns.
- [ ] Write RED tests for exact expected indexes and absence of duplicates.
- [ ] Add only justified indexes for update claims, memberships, daily activity, rankings, pending achievements, due notifications/subscriptions, owner search, and Telegram charge IDs.
- [ ] Document query patterns and rollback-safe downgrade.
- [ ] Run Alembic empty/previous-schema upgrades.
- [ ] Commit `perf: add audited production indexes`.

### Task 11: Separate Migrations from Application Startup

**Files:**
- Modify: `Dockerfile`
- Create: `scripts/container-entrypoint.sh`
- Create: `scripts/run-migrations.sh`
- Create: `tests/test_migration_safe_startup.py`
- Create: `.github/workflows/deploy-cloud-run.yml`

**Interfaces:**
- Application entrypoint starts Uvicorn only.
- Migration command uses the same image with `scripts/run-migrations.sh`.
- Deployment workflow builds/tag by SHA and version, runs one migration job, deploys zero traffic, smokes, then shifts traffic.

- [ ] Write RED tests proving app startup contains no Alembic invocation and migration script does.
- [ ] Split entrypoints and retain non-root execution.
- [ ] Add backward-compatibility migration check in CI.
- [ ] Implement manual/authorized Cloud Run deployment workflow with immutable digest, previous revision capture, zero-traffic deploy, health/ready/static/OpenAPI smoke, and rollback command output.
- [ ] Verify workflow contains no secrets in artifacts/logging commands.
- [ ] Commit `deploy: separate migrations and rollback-safe release`.

### Task 12: Add Diagnostics and Strong Readiness

**Files:**
- Modify: `app/main.py`
- Create: `app/api/diagnostics.py`
- Create: `app/operations/readiness.py`
- Create: `tests/test_readiness_dependencies.py`
- Create: `tests/test_diagnostics.py`

**Interfaces:**
- `/health` remains external-call-free.
- `/ready` checks initialized flag, DB, Alembic revision, and required Redis.
- `/internal/diagnostics` requires the metrics/internal token and returns only version, build SHA, environment, revision, migration revision, dependency status, and latency.

- [ ] Write RED tests for each degraded dependency, optional Redis, revision mismatch, no exception/URL leakage, and protected diagnostics.
- [ ] Implement bounded-time dependency probes.
- [ ] Keep liveness unchanged.
- [ ] Verify 503 and safe payloads.
- [ ] Commit `feat: strengthen production readiness diagnostics`.

### Task 13: Add Load and Resilience Test Packages

**Files:**
- Modify: `pyproject.toml`, `requirements.lock`
- Create: `load/locustfile.py`
- Create: `load/identities.py`
- Create: `load/scenarios/*.py`
- Create: `load/seeding.py`
- Create: `load/validate_report.py`
- Create: `tests/test_load_support.py`
- Create: `.github/workflows/staging-load.yml`
- Create: `docs/LOAD_TESTING.md`

**Interfaces:**
- Signed test init data is generated from an explicitly test-only bot token.
- Local smoke launches a disposable SQLite app and never creates real payments.
- Reports are JSON/CSV without user content or credentials.

- [ ] Write RED tests for deterministic identity signing, duplicate webhook fixtures, seeded correctness invariants, and report validation.
- [ ] Add `locust>=2.31,<3` to dev dependencies.
- [ ] Implement home/groups/group/achievement/write/webhook/owner/invoice-limit scenarios.
- [ ] Add short CI smoke and manual 15-minute staging workflow.
- [ ] Enforce error-rate/correctness/p95 criteria without flaky local absolute latency gates.
- [ ] Commit `test: add production load and resilience profiles`.

### Task 14: Add Backup and Restore Verification

**Files:**
- Create: `scripts/verify_restore.py`
- Create: `tests/test_restore_verification.py`
- Create: `.github/workflows/verify-restore.yml`
- Create: `docs/OPERATIONS.md`

**Interfaces:**
- Script refuses URLs equal to `DATABASE_URL` or hosts/names marked production unless `--allow-production` is supplied; CI never supplies it.
- Checks Alembic revision, critical tables, row-count sanity, duplicate Telegram charge IDs, and payment reconciliation summary.
- Outputs only counts and status.

- [ ] Write RED tests for production refusal, schema mismatch, missing table, negative/unreasonable counts, duplicate charge IDs, and successful disposable restore.
- [ ] Implement async verification with no row data output.
- [ ] Add protected manual workflow and quarterly drill template.
- [ ] Document RPO 24 hours, RTO 4 hours, ownership, emergency steps, and forward-fix policy.
- [ ] Commit `ops: add backup restore verification`.

### Task 15: Complete Security Hardening and Automated Gates

**Files:**
- Create: `app/security/headers.py`
- Modify: `app/main.py`
- Create: `tests/test_security_headers.py`
- Create: `scripts/secret_scan.py`
- Create: `.github/workflows/security.yml`
- Create: `docs/security-audit-0.15.0.md`

**Interfaces:**
- API responses use no-sniff, no-referrer, frame restrictions, and safe cache policies.
- Mini App CSP permits only required Telegram/Vite production assets and denies object/embed/base injection.
- Security workflow runs `pip-audit`, `npm audit --omit=dev`, secret scan, container non-root/minimal-content smoke, authorization/billing regressions, and production-bypass checks.

- [ ] Write RED tests for API/static security headers, CSP, internal endpoint authorization, production bypass absence, and scanner fixtures.
- [ ] Implement middleware/header policy without breaking Telegram Mini App.
- [ ] Add deterministic secret scanner exclusions for known fake test values only.
- [ ] Add dependency and container gates.
- [ ] Produce a source-backed audit report with accepted findings section empty by default.
- [ ] Commit `security: enforce final production audit gates`.

### Task 16: Final CI, Version, Documentation, and Delivery

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `VERSION`
- Modify: `README.md`
- Modify: `.env.example`
- Create: `docs/OBSERVABILITY.md`
- Create: `docs/releases/0.15.0.md`
- Modify: PR #37 metadata after Architecture 2.0 merge

**Interfaces:**
- Exact version `0.15.0` appears in package metadata, runtime diagnostics, image labels, docs, and load reports.
- PR CI uses `permissions: contents: read`.

- [ ] Add required read-only CI jobs: frontend, WebKit, Ruff, pytest, repeated concurrency, compileall, empty/previous migration, security, secret scan, Docker build, non-root smoke, load smoke, and artifact cleanliness.
- [ ] Update all configuration and operational documentation.
- [ ] Run complete backend/frontend/browser/migration/security/load/Docker verification on one exact SHA.
- [ ] Confirm no temporary archives, apply scripts, diagnostic logs, reports, local databases, credentials, or self-mutating workflow remain.
- [ ] After PR #36 is green and merged, rebase/merge onto `main`, retarget PR #37, rerun every check, and merge only on the exact green head.
- [ ] Commit `release: prepare ChatPulse 0.15.0`.

## Plan Self-Review

- All fourteen acceptance criteria map to explicit tasks.
- Redis failure policies are covered separately for reads, writes, billing, scheduler jobs, and readiness.
- Multi-instance leases and atomic rate limits use Redis Lua and token ownership.
- Observability includes request IDs, structured logs, scrubbing, Sentry, bounded metrics, DB timing, and documented SLOs.
- Migrations are removed from application startup and receive a dedicated immutable-image release step.
- Load, restore, security, container, and rollback gates are independently testable.
- No task stores or emits message content, init data, raw Telegram payloads, credentials, or customer data.
- The final merge remains blocked on Architecture 2.0 merge and exact-head verification.
