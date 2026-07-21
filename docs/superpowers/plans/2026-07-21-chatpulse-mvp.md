# ChatPulse MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a deployable Telegram group activity bot with automatic registration, activity persistence, and basic rankings.

**Architecture:** FastAPI receives Telegram webhooks and forwards updates to aiogram routers. Async SQLAlchemy repositories persist metadata and counters, while a small statistics service converts query results into command responses.

**Tech Stack:** Python 3.12, aiogram 3, FastAPI, SQLAlchemy 2 async, aiosqlite, asyncpg, pydantic-settings, pytest, pytest-asyncio, httpx, Ruff, Docker.

## Global Constraints

- Do not store message text, captions, or media files.
- Ignore bot-authored messages and commands in activity counters.
- Activate tracking only while ChatPulse is a group administrator.
- Use webhook delivery and listen on the Cloud Run `PORT` environment variable.
- Keep secrets out of source control.

---

### Task 1: Project configuration and application health

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/main.py`
- Test: `tests/test_health.py`

**Interfaces:**
- Produces: `Settings`, `create_app(settings: Settings | None = None) -> FastAPI`.

- [ ] Write a failing API test asserting `GET /health` returns `{"status": "ok", "service": "chatpulse"}`.
- [ ] Run `pytest tests/test_health.py -v` and confirm failure because the application does not exist.
- [ ] Add minimal configuration and FastAPI app implementation.
- [ ] Re-run the test and confirm it passes.

### Task 2: Persistence and activity counters

**Files:**
- Create: `app/database.py`
- Create: `app/models.py`
- Create: `app/repositories/__init__.py`
- Create: `app/repositories/activity.py`
- Test: `tests/test_activity_repository.py`

**Interfaces:**
- Produces: `Database`, `ActivityRepository.upsert_user`, `upsert_group`, `record_message`, `get_member_stats`, `get_group_summary`, and `get_top_members`.

- [ ] Write failing async tests for idempotent user/group upserts and message/media/reply counter increments.
- [ ] Run the repository tests and confirm imports or assertions fail.
- [ ] Implement SQLAlchemy models, database lifecycle, and repository operations.
- [ ] Re-run repository tests and confirm they pass.

### Task 3: Statistics formatting

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/stats.py`
- Test: `tests/test_stats_service.py`

**Interfaces:**
- Consumes repository summary dictionaries.
- Produces `format_group_stats`, `format_top_members`, and `format_member_stats`.

- [ ] Write failing formatting tests for normal and empty statistics.
- [ ] Run the tests and confirm failure.
- [ ] Implement deterministic Ukrainian text formatting.
- [ ] Re-run the tests and confirm they pass.

### Task 4: Telegram registration and group tracking

**Files:**
- Create: `app/bot/__init__.py`
- Create: `app/bot/keyboards.py`
- Create: `app/bot/routers/__init__.py`
- Create: `app/bot/routers/private.py`
- Create: `app/bot/routers/groups.py`
- Create: `app/bot/setup.py`
- Modify: `app/main.py`
- Test: `tests/test_message_classification.py`
- Test: `tests/test_webhook_security.py`

**Interfaces:**
- Produces: `build_dispatcher(repository) -> Dispatcher`, `classify_message(message) -> MessageActivity | None`, and the secured webhook route.

- [ ] Write failing tests proving commands and bots are ignored and media/replies are classified correctly.
- [ ] Write a failing API test proving an incorrect webhook secret returns HTTP 403.
- [ ] Implement routers, keyboards, dispatcher setup, webhook parsing, and secret validation.
- [ ] Run the focused tests and confirm they pass.

### Task 5: Deployment and documentation

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `README.md`
- Test: full project checks.

**Interfaces:**
- Produces a Cloud Run-ready container started by `uvicorn app.main:app`.

- [ ] Add container configuration and complete local/Cloud Run setup instructions.
- [ ] Run `pytest -q` and confirm zero failures.
- [ ] Run `ruff check .` and confirm zero errors.
- [ ] Run `python -m compileall app` and confirm successful compilation.
