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

**Status:** completed in PR #37.

**Delivered:** read-only CI, no self-mutating apply job, no startup migration in Docker CMD, version contract `0.15.0`, artifact-cleanliness tests, inherited Ruff cleanup, and frontend typecheck repair.

### Task 2: Add Redis Runtime and Dependency Lifecycle

**Status:** implementation in progress.

**Delivered:** Redis settings, pinned Redis dependency, optional/required failure policy, key prefixing, bounded client configuration, lifecycle tests.

**Remaining:** wire runtime into FastAPI lifespan and `/ready`.

### Task 3: Implement Token-Owned Distributed Leases

**Status:** implementation in progress.

**Delivered:** `LeaseService`, token-owned acquire/renew/release Lua behavior, contention and fail-closed tests.

**Remaining:** wire leases into weekly reports, retention, VIP lifecycle, and recurring singleton jobs.

### Task 4: Add Atomic Policy-Based Rate Limiting

**Status:** pending.

### Task 5: Add Webhook Backpressure and Body Protection

**Status:** pending.

### Task 6: Implement Structured Logging, Request IDs, and Redaction

**Status:** pending.

### Task 7: Add Protected Prometheus Metrics

**Status:** pending.

### Task 8: Add Scrubbed Optional Sentry Integration

**Status:** pending.

### Task 9: Harden Database Runtime and Query Instrumentation

**Status:** pending.

### Task 10: Audit and Add High-Traffic Database Indexes

**Status:** pending.

### Task 11: Separate Migrations from Application Startup

**Status:** partially completed; Docker CMD no longer runs Alembic. Dedicated release workflow remains pending.

### Task 12: Add Load and Resilience Testing

**Status:** pending.

### Task 13: Add Backup and Restore Verification

**Status:** pending.

### Task 14: Add Final Security and Supply-Chain Gates

**Status:** pending.

### Task 15: Documentation, Exact-Head Verification, and Delivery

**Status:** pending and blocked from merge until Architecture 2.0 is merged.

## Plan Self-Review

- Every approved design section maps to a task.
- Redis failure policies, rate limits, labels, readiness, pool values, release order, RPO/RTO, and rollback conditions remain exact.
- No task allows Redis to replace PostgreSQL correctness.
- No temporary workflow or generated transport may survive final delivery.
- The third stage cannot merge before Architecture 2.0.
