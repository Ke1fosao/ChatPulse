# ChatPulse Production & Scale 3.0 Design

## Status

Scope approved by the owner on 2026-07-26. This document is the implementation contract for the final hardening stage and requires written-spec review before the implementation plan begins.

## Dependency and Delivery Model

Production & Scale 3.0 is developed on the stacked branch `production/chatpulse-3-0`, based on the exact head of `architecture/chatpulse-2-0` at commit `2c3d572b7813216b2981a2b93e0cfbf5aaeea012`.

The stage must not be merged into `main` before Architecture 2.0 is green and merged. After that merge, the branch is rebased or merged onto the new `main`, its pull request is retargeted to `main`, and every verification job is rerun on the resulting exact head.

The temporary self-mutating Architecture 2.0 workflow must not survive into the final Production & Scale 3.0 pull request. Production CI must use read-only source checkout and must never commit generated implementation changes from GitHub Actions.

## Goal

Make ChatPulse safe to run as multiple Cloud Run instances, observable during incidents, resistant to abuse, measurable under load, and recoverable after a failed deployment or database incident.

The release version becomes `0.15.0`.

## Non-Goals

This stage does not add new user-facing product features, alter XP formulas, change VIP prices, redesign Mini App screens, store message text, replace PostgreSQL/Supabase, or split the application into independent deployable microservices.

Redis is an operational coordination layer. It never becomes the source of truth for user identity, billing, XP, achievements, permissions, or durable analytics.

## Current Production Risks

1. Process-local caches and keyed locks do not coordinate multiple Cloud Run instances.
2. There is no shared rate limiter for Mini App, owner, billing, and administrative writes.
3. Application logs are mostly plain text and there is no stable request correlation identifier.
4. There is no protected metrics endpoint, alert-ready metric naming, or integrated error tracking boundary.
5. The production container runs `alembic upgrade head` in every application instance, so concurrent startup can race migrations and couples application availability to migration execution.
6. Database pool size, overflow, acquisition timeout, statement timeout, and slow-query thresholds are not explicitly configured.
7. There is no repeatable load test for webhook, Mini App reads, or write-heavy paths.
8. Backup ownership, recovery targets, restore verification, and rollback steps are not encoded as an operational runbook.
9. CI does not currently enforce dependency vulnerability checks, migration safety checks, or a production smoke test on the built image.

## Approaches Considered

### A. Incremental production platform inside the current service — selected

Keep one FastAPI/aiogram service and add focused operational modules: Redis coordination, rate limiting, structured observability, explicit database runtime settings, load tests, release workflows, and recovery documentation.

Advantages:

- lowest migration risk;
- preserves current product behavior and deployment topology;
- can be tested incrementally;
- avoids duplicating business logic across services;
- appropriate for the current ChatPulse scale.

Trade-off: one deployment still contains webhook, API, scheduler endpoints, and Mini App static delivery.

### B. Immediate microservice split — rejected

Separate webhook ingestion, scheduler, Mini App API, and workers into independent deployments.

Advantages: independent scaling and failure isolation.

Rejected because it introduces queues, cross-service contracts, more secrets, more deployments, and significantly larger incident surface before current operational basics are complete.

### C. Monitoring-only hardening — rejected

Add error tracking and dashboards without Redis, rate limits, deployment separation, recovery drills, or load tests.

Rejected because it would reveal failures but would not prevent duplicate scheduled work, abuse, migration races, or untested capacity limits.

## Architecture Overview

Production & Scale 3.0 adds six operational boundaries:

1. `RedisRuntime` — shared ephemeral coordination and cache access.
2. `RateLimitService` — atomic Redis token-bucket limits with explicit endpoint policies.
3. `LeaseService` — token-owned distributed leases for scheduled jobs and singleton operations.
4. `Observability` — JSON logs, request IDs, metrics, slow-query reporting, and scrubbed error tracking.
5. `DatabaseRuntime` — explicit pool/timeouts and migration-safe startup.
6. `ReleaseOperations` — load tests, security checks, backup verification, immutable deployment, smoke tests, and rollback instructions.

## 1. Redis Runtime

### Configuration

Add these settings:

- `REDIS_URL`
- `REDIS_REQUIRED`
- `REDIS_KEY_PREFIX`, default `chatpulse:v1`
- `REDIS_CONNECT_TIMEOUT_SECONDS`, default `2`
- `REDIS_SOCKET_TIMEOUT_SECONDS`, default `2`
- `REDIS_MAX_CONNECTIONS`, default `20`

Development and tests may run without Redis when `REDIS_REQUIRED=false`. Production documentation requires `REDIS_REQUIRED=true`.

Use `redis.asyncio` from `redis>=5,<6`. One connection pool is created during FastAPI lifespan and closed during shutdown.

### Key Rules

All keys use the configured prefix and a versioned namespace. Keys must have finite TTLs except connection metadata managed by the Redis client.

No key contains bot tokens, Mini App init data, message text, captions, file content, payment payloads, or private notes.

### Failure Policy

- authorization, billing, XP, and durable writes never depend exclusively on Redis;
- cache reads fail open to the authoritative database or Telegram API;
- rate limiting logs a degraded event and follows the endpoint policy below;
- singleton scheduler leases fail closed, so a job is skipped rather than executed without coordination;
- readiness fails when `REDIS_REQUIRED=true` and Redis cannot be reached.

## 2. Distributed Leases

Add a token-owned lease using Redis `SET key token NX PX ttl` and a Lua compare-and-delete release operation. Renewal also verifies the token.

Use leases for:

- weekly report scheduler execution;
- retention notification scheduler execution;
- rank snapshot generation;
- recurring expiry/lifecycle notification batches;
- any future singleton maintenance command.

Lease names are operation-based and time-bucketed where appropriate. Example: `lease:weekly-reports:2026-31`.

The lease TTL must exceed the normal job duration and support bounded renewal. A lost lease stops the next batch boundary and records a warning.

PostgreSQL row locks and unique constraints remain the source of truth for XP, payments, achievement unlocks, webhook delivery, and database mutations. Redis leases must not replace those protections.

## 3. Rate Limiting and Backpressure

### Algorithm

Use one atomic Redis Lua token-bucket implementation. The result contains `allowed`, `remaining`, and `retry_after_seconds`.

Rate-limit responses use HTTP `429`, a stable JSON error code `RATE_LIMITED`, and a `Retry-After` header. User-facing messages remain Ukrainian.

### Policies

- authenticated Mini App reads: 120 requests per minute per Telegram user, burst 30;
- authenticated Mini App writes: 30 requests per minute per Telegram user, burst 10;
- billing and invoice creation: 10 requests per minute per Telegram user, burst 3;
- owner and staff non-destructive actions: 60 requests per minute per actor;
- owner destructive or bulk actions: 10 requests per minute per actor, burst 3;
- unauthenticated invalid Mini App authentication attempts: 30 attempts per 5 minutes per remote address;
- internal scheduler endpoints: 30 requests per minute per authenticated scheduler identity.

The Telegram webhook is not rejected by a normal user rate limit because Telegram retries could amplify failures. Instead it receives:

- verified path and header secrets before dispatcher work;
- maximum request body size of 512 KiB;
- a bounded in-process concurrency semaphore;
- durable update claim/lease protection from Stability 1.0;
- metrics for queue wait, active handlers, failures, and retries.

When Redis is temporarily unavailable, authenticated product reads fail open, while billing, destructive owner actions, and internal scheduler actions fail closed with `503 OPERATIONAL_DEPENDENCY_UNAVAILABLE`.

Remote-address limiting uses the direct ASGI client address by default. Proxy headers are trusted only when an explicit `TRUST_PROXY_HEADERS=true` production setting is enabled for the known Cloud Run environment.

## 4. Observability

### Structured Logging

Use JSON logs in production and readable console logs in development.

Each HTTP request receives a validated or generated `request_id`. The response includes `X-Request-ID`. Logs include:

- timestamp;
- level;
- event;
- request ID;
- route template;
- method;
- status code;
- duration;
- application version;
- environment;
- Cloud Run revision when available.

Webhook processing additionally includes update ID and update type. User IDs, chat IDs, and payment identifiers may appear only as separately named numeric identifiers, never as high-cardinality metric labels.

Logs must never contain bot tokens, authorization headers, scheduler secrets, raw webhook bodies, Mini App init data, raw Telegram user objects, payment payloads, or private notes.

### Error Tracking

Add optional Sentry integration controlled by:

- `SENTRY_DSN`
- `SENTRY_ENVIRONMENT`
- `SENTRY_TRACES_SAMPLE_RATE`, default `0.05`

The integration removes headers, cookies, query strings containing init data, request bodies, Telegram payloads, and configured secrets before an event is sent.

Expected `4xx` responses, validation errors, rate limits, account blocks, and permission denials are not reported as application exceptions.

### Metrics

Expose Prometheus text metrics at `/internal/metrics`. The endpoint is disabled unless `METRICS_ENABLED=true` and requires `Authorization: Bearer <INTERNAL_METRICS_TOKEN>`.

Metrics use bounded labels only. Required metrics:

- HTTP request count and duration by route template, method, and status class;
- webhook received, completed, retried, duplicate, lease-conflict, and failed counts;
- webhook active handlers and queue wait duration;
- Redis operation failures and latency by operation class;
- rate-limit allowed and rejected counts by policy;
- distributed lease acquired, skipped, renewed, and lost counts by operation;
- Telegram API call count, duration, failure, cache hit, cache stale, and cache miss;
- database checkout wait and slow-query counts;
- transaction rollback counts by operation;
- scheduler job duration and outcome;
- Mini App API error counts by stable error code.

No metric label contains request IDs, Telegram IDs, chat IDs, usernames, invoice IDs, or raw paths with IDs.

### Initial Service-Level Objectives

These are operational targets, not flaky unit-test thresholds:

- availability: 99.9% monthly for `/health` and authenticated core API;
- server error rate: below 1% over 15 minutes;
- cached Mini App read p95: below 750 ms;
- group-list read p95: below 1.5 s;
- webhook handler p95 excluding Telegram retries: below 2 s;
- scheduler duplicate execution: zero.

## 5. Database Runtime and Query Performance

Add explicit settings:

- `DB_POOL_SIZE`, default `5`;
- `DB_MAX_OVERFLOW`, default `5`;
- `DB_POOL_TIMEOUT_SECONDS`, default `10`;
- `DB_POOL_RECYCLE_SECONDS`, default `1800`;
- `DB_STATEMENT_TIMEOUT_MS`, default `15000`;
- `DB_SLOW_QUERY_MS`, default `500`.

SQLite keeps its current local timeout behavior and does not receive PostgreSQL-only pool options.

PostgreSQL connections use `pool_pre_ping`, bounded pool settings, application name `chatpulse/<version>`, and a transaction-local statement timeout. The Supabase pooler compatibility setting disables asyncpg prepared-statement caching when configured.

Add SQLAlchemy instrumentation that records query duration and emits a scrubbed `database_slow_query` event containing operation type and normalized table names, not SQL parameters.

Create an index audit focused on the real high-traffic paths:

- webhook update claim and lease lookup;
- group membership lookups;
- daily activity by group/user/date;
- rankings by group and XP/activity fields;
- pending achievement events;
- due notifications and subscriptions;
- owner user search/filter paths;
- payment lookup by Telegram charge ID.

Every new index must be justified by a test fixture or an `EXPLAIN` artifact in documentation. Duplicate and unused indexes are not added speculatively.

## 6. Migration-Safe Startup and Deployment

The application container no longer runs `alembic upgrade head` in its `CMD`.

Migrations run exactly once in a dedicated release step or Cloud Run Job before traffic is shifted. The migration step uses the same immutable image as the application revision.

The release sequence is:

1. build one image tagged with the exact Git SHA and version;
2. run unit, integration, browser, migration, security, and image smoke checks;
3. record the current production revision and image digest;
4. run `alembic upgrade head` as a single migration job;
5. deploy a new revision with zero traffic;
6. run `/health`, `/ready`, Mini App static, OpenAPI, and authenticated staging smoke checks;
7. shift traffic gradually when the platform supports it, otherwise shift only after all smoke checks pass;
8. watch error rate and latency during the verification window;
9. keep the previous revision available for immediate traffic rollback.

Database migrations in this stage must be backward-compatible with the previous application revision. Destructive column removal and irreversible data rewrites are forbidden in the same release that stops old-code compatibility.

Code rollback routes traffic to the previous revision. Database downgrade is not automatic. Recovery uses forward-fix migrations unless a separately tested downgrade exists.

## 7. Load and Resilience Testing

Add a `load/` package using Locust with reusable signed Telegram Mini App test identity generation and seeded staging data.

Scenarios:

- home/profile read traffic;
- groups list with several groups;
- group overview/ranking/analytics reads;
- achievement collection reads;
- favorite/settings writes;
- webhook burst with unique and duplicate update IDs;
- owner user search and filtered pagination;
- invoice creation rate-limit behavior without completing real payments.

CI runs a short local smoke load against a disposable SQLite-backed application and verifies:

- zero unexpected request failures;
- no duplicate webhook side effects;
- no XP invariant violations;
- rate-limit responses appear only after the configured budget;
- application remains ready after the run.

A manual staging workflow runs the longer performance profile. It records a machine-readable report and enforces:

- error rate below 1%;
- no correctness invariant failures;
- p95 within the documented SLO for the tested endpoint class;
- no unbounded memory or connection growth during a 15-minute steady-state run.

Absolute local CI latency thresholds remain generous to avoid runner noise. Production SLO thresholds are enforced in staging, not unit tests.

## 8. Backup and Recovery

### Targets

Initial operational targets:

- recovery point objective: 24 hours for full database loss;
- recovery time objective: 4 hours;
- no loss target for successfully recorded Telegram Stars payments, using Telegram charge IDs and provider records for reconciliation.

### Responsibilities

Supabase managed backups remain the primary database backup mechanism. The repository adds verification and recovery tooling rather than exporting production data into GitHub artifacts.

Add:

- `docs/OPERATIONS.md` with backup ownership, provider checks, emergency contacts, and recovery commands;
- a restore verification script that connects only to an explicitly supplied restored or staging database;
- schema revision validation through Alembic;
- critical table existence and row-count sanity checks;
- payment reconciliation checks by unique Telegram charge ID;
- a manual GitHub workflow that runs restore verification using protected environment secrets;
- a quarterly restore-drill checklist with date, duration, result, and discovered issues.

Production database dumps, credentials, and customer data must never be uploaded as GitHub Actions artifacts.

## 9. Security Hardening

The final security audit covers:

- dependency vulnerabilities with `pip-audit` and `npm audit --omit=dev`;
- secret scanning in tracked files and generated artifacts;
- container execution as non-root;
- minimal production image contents;
- response security headers for Mini App and API;
- strict request body limits;
- CORS remaining closed unless explicitly required;
- trusted proxy configuration;
- owner/staff authorization and immutable owner guarantees;
- billing idempotency and refund paths;
- metrics and internal scheduler endpoint protection;
- Redis TLS requirements in production;
- log and Sentry scrubbing tests;
- absence of development authentication bypasses in production builds.

Automated audit failures block merge unless the finding is documented, time-bounded, and accepted by the owner in the pull request.

## 10. Health and Readiness

`/health` remains a process liveness endpoint and does not call external services.

`/ready` checks:

- application lifespan initialization;
- database connectivity;
- current Alembic revision compatibility;
- Redis connectivity only when `REDIS_REQUIRED=true`.

Readiness results expose dependency names and status without URLs, credentials, or exception details. Failure returns `503`.

A separate protected diagnostics endpoint may expose build SHA, version, environment, revision, migration revision, and dependency latency to the owner. It must not expose secrets or raw configuration.

## 11. Testing Strategy

### Unit and Integration

- Redis connection lifecycle and failure modes;
- rate-limit token bucket atomicity and retry timing;
- fail-open and fail-closed policy tests;
- lease acquisition, contention, renewal, expiry, and token-safe release;
- request ID propagation;
- log redaction and Sentry scrubbing;
- metric label cardinality rules;
- readiness dependency behavior;
- database pool configuration and slow-query events;
- scheduler duplicate prevention across two application instances;
- migration compatibility with the previous release;
- rollback-safe application startup without automatic migration;
- backup restore verification against a disposable database.

### Existing Regression Suite

All Architecture 2.0 backend tests, frontend tests, TypeScript typecheck, Vite build, Playwright WebKit tests, Alembic upgrade tests, and Docker build must remain green.

### Repeated Concurrency Verification

Concurrency-sensitive Redis, webhook, scheduler, XP, and billing tests run repeatedly. A single intermittent invariant failure blocks release.

## 12. CI and Release Gates

The final CI pipeline has read-only repository permissions unless a specific release job requires otherwise.

Required jobs on the exact pull request head:

- frontend tests;
- TypeScript typecheck;
- production frontend build;
- Playwright WebKit;
- Ruff lint;
- Ruff formatting check;
- complete pytest suite;
- repeated concurrency tests;
- Python compileall;
- Alembic upgrade from an empty database;
- Alembic upgrade from the previous release schema;
- dependency security audit;
- secret scan;
- Docker image build;
- container smoke test as non-root;
- local load smoke;
- generated artifact cleanliness check.

The draft pull request becomes ready only when all required jobs are green on one exact head SHA and no temporary apply scripts, archives, diagnostic logs, test reports, local databases, tokens, or self-mutating workflows remain in the diff.

## 13. Rollout and Rollback

Rollout begins with staging. Production deployment uses a new Cloud Run revision and an immutable image digest.

Immediate rollback conditions:

- readiness failure;
- server error rate above 2% for 5 minutes;
- p95 latency more than double the baseline for 10 minutes;
- webhook failures or retries increasing continuously;
- duplicate scheduler execution;
- payment, XP, or achievement invariant failure;
- Redis failure causing protected operations to become unsafe.

Rollback returns traffic to the previous revision. The incident is recorded with request IDs, revision IDs, metric snapshots, and the database migration state.

## 14. Documentation Deliverables

- updated `README.md` production configuration;
- `.env.example` with safe defaults and explanations;
- `docs/OPERATIONS.md` incident, backup, restore, deployment, and rollback runbook;
- `docs/OBSERVABILITY.md` events, metrics, dashboards, and alerts;
- `docs/LOAD_TESTING.md` local and staging execution;
- release notes for `0.15.0`;
- exact deployment and rollback evidence in the pull request.

## Acceptance Criteria

Production & Scale 3.0 is complete only when:

1. two application instances coordinate scheduled jobs through Redis without duplicate execution;
2. rate limiting is atomic, policy-specific, tested, and returns stable errors;
3. Redis failure behavior matches documented fail-open/fail-closed rules;
4. JSON logs, request IDs, protected metrics, and scrubbed error tracking are operational;
5. database pools and statement timeouts are explicit and tested;
6. application instances start without running migrations;
7. a dedicated migration release step and rollback-safe deployment workflow exist;
8. load smoke and staging performance tests pass;
9. backup restore verification succeeds on a non-production database;
10. security audit gates pass;
11. the entire existing regression suite passes;
12. the production image runs as non-root and passes health/readiness smoke tests;
13. version `0.15.0` is consistent across code, image, documentation, and diagnostics;
14. the final pull request is based on merged Architecture 2.0 and is green on its exact head.

## Spec Self-Review

- No placeholder, TODO, or unspecified implementation dependency remains.
- Redis is explicitly limited to ephemeral coordination and does not replace database correctness.
- Multi-instance scheduling, rate limits, observability, database runtime, migrations, load testing, backup recovery, security, deployment, and rollback are all covered.
- Failure policies are explicit for Redis, database, webhook, billing, and scheduler paths.
- The design preserves current product behavior and privacy guarantees.
- The scope is large but cohesive: every item serves production operation and scale rather than unrelated product development.
