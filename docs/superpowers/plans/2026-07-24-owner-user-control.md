# Owner User Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build complete, server-enforced user administration for ChatPulse Owner Control and merge it safely into `main`.

**Architecture:** Add focused user-control models and a repository that owns staff authorization, blocking, user details, notes/tags, XP adjustments, messaging, filters, sorting, and bulk operations. Enforce blocks in both Mini App authorization and Aiogram middleware. Keep existing Owner overview, groups, VIP, revenue, and audit behavior compatible while replacing the simple user modal with a permission-aware mobile drawer.

**Tech Stack:** Python 3.12, FastAPI, Aiogram 3, SQLAlchemy async, PostgreSQL/Supabase, React, TypeScript, Vite, Vitest.

## Global Constraints

- The singleton Owner is immutable and cannot be blocked, demoted, or targeted by bulk destructive actions.
- Blocking denies the Telegram bot and Mini App, including XP, streak, achievement, and analytics processing.
- Every mutation requires server-side permissions and produces audit history.
- Existing VIP and Owner Revenue API behavior must remain compatible.
- No ordinary Telegram conversation content is stored; only admin-authored outbound messages may be persisted for delivery history.
- Merge only after frontend, backend, Docker, and CI checks pass.

---

### Task 1: Persistence and permission foundation

**Files:**
- Create: `app/user_control_models.py`
- Create: `app/services/admin_access.py`
- Modify: `app/database.py`
- Create: `supabase/migrations/20260724010000_add_owner_user_control.sql`
- Test: `tests/test_admin_access.py`

**Interfaces:**
- Produces: `AdminRole`, `AdminActor`, `ROLE_PERMISSIONS`, and SQLAlchemy models for staff, restrictions, notes, tags, XP adjustments, message deliveries, and blocked-access events.

- [ ] Write failing tests for the Owner permission set, fixed role matrix, staff lookup, and immutable Owner behavior.
- [ ] Run `pytest tests/test_admin_access.py -q` and confirm failure before implementation.
- [ ] Add the models, check constraints, indexes, role permission map, and actor resolver.
- [ ] Import the model module from `app/database.py` so test schema creation includes every table.
- [ ] Add the matching idempotent Supabase migration with RLS enabled and service-role-only policies.
- [ ] Run `pytest tests/test_admin_access.py -q` and confirm pass.
- [ ] Commit with `feat: add user control persistence and permissions`.

### Task 2: Full blocking across Mini App and bot

**Files:**
- Create: `app/repositories/user_control.py`
- Create: `app/bot/middlewares/user_restrictions.py`
- Modify: `app/api/miniapp/dependencies.py`
- Modify: `app/bot/setup.py`
- Modify: `app/main.py`
- Test: `tests/test_user_restrictions.py`
- Test: `tests/test_bot_user_restriction_middleware.py`

**Interfaces:**
- Produces: `UserControlRepository.is_blocked`, `block_user`, `unblock_user`, `record_blocked_access`, and `BlockedUserMiddleware`.

- [ ] Write failing repository tests for block/unblock, Owner protection, audit entries, and coalesced access events.
- [ ] Write failing middleware and Mini App dependency tests proving blocked users never reach handlers.
- [ ] Implement restriction queries and transactional mutations with exact confirmation/reason validation delegated from API schemas.
- [ ] Enforce `ACCOUNT_BLOCKED` after Telegram init-data validation and before Mini App route execution.
- [ ] Register `BlockedUserMiddleware` as an outer dispatcher middleware so group activity is stopped before routers and repositories.
- [ ] Wire one shared repository into FastAPI state and dispatcher data.
- [ ] Run the focused tests and commit with `feat: enforce full user blocking`.

### Task 3: Detailed users API, filters, sorting, notes, tags, XP, roles, and messages

**Files:**
- Modify: `app/repositories/user_control.py`
- Modify: `app/api/owner/dependencies.py`
- Modify: `app/api/owner/schemas.py`
- Modify: `app/api/owner/routes.py`
- Modify: `app/main.py`
- Test: `tests/test_owner_user_control_api.py`
- Test: `tests/test_user_control_repository.py`

**Interfaces:**
- Consumes: `AdminActor` and the role permission map from Task 1.
- Produces: permission-aware endpoints under `/api/owner/v1/users` and a complete user detail payload.

- [ ] Write failing tests for actor access, permission denials, user detail, payment summary, filters, sorting, pagination, and user-scoped audit.
- [ ] Write failing tests for notes, tags, staff role assignment, XP adjustments, and direct message delivery results.
- [ ] Replace owner-only dependency with actor resolution while retaining Owner compatibility.
- [ ] Implement SQL filters for VIP, blocked/inactive status, role, payer status, dates, tags, and all specified sort modes.
- [ ] Build detail queries for identity, group membership, billing summary, restriction, role, notes/tags, adjustments, deliveries, and audit.
- [ ] Implement transactional note/tag/role/XP mutations and recalculate levels with the existing formula.
- [ ] Implement safe plain-text Telegram delivery through `request.app.state.bot`, persist results, and audit the action.
- [ ] Run focused backend tests and commit with `feat: add complete user administration api`.

### Task 4: Bulk operations

**Files:**
- Modify: `app/repositories/user_control.py`
- Modify: `app/api/owner/schemas.py`
- Modify: `app/api/owner/routes.py`
- Test: `tests/test_owner_user_bulk_api.py`

**Interfaces:**
- Produces: `POST /api/owner/v1/users/bulk` returning `succeeded` and `failed` target arrays.

- [ ] Write failing tests for target caps, Owner exclusion, permission checks, VIP, block/unblock, tag, and message batches.
- [ ] Implement independent per-target processing with one parent batch audit event and individual mutation audit entries.
- [ ] Limit general batches to 100 users and message batches to 50.
- [ ] Preserve successful targets when another target fails.
- [ ] Run focused tests and commit with `feat: add safe owner bulk actions`.

### Task 5: Owner Control user interface

**Files:**
- Modify: `miniapp/src/owner/types.ts`
- Modify: `miniapp/src/owner/ownerApi.ts`
- Modify: `miniapp/src/owner/OwnerApp.tsx`
- Modify: `miniapp/src/owner/OwnerUsers.tsx`
- Create: `miniapp/src/owner/OwnerUserCard.tsx`
- Create: `miniapp/src/owner/OwnerUserDrawer.tsx`
- Create: `miniapp/src/owner/OwnerUserActions.tsx`
- Create: `miniapp/src/owner/OwnerUserActionModal.tsx`
- Create: `miniapp/src/owner/OwnerBulkBar.tsx`
- Create: `miniapp/src/owner/OwnerBulkModal.tsx`
- Modify: `miniapp/src/styles/owner.css`
- Modify: `miniapp/src/styles/owner-mobile.css`
- Test: `miniapp/src/owner/OwnerUsers.test.tsx`
- Test: `miniapp/src/owner/OwnerUserDrawer.test.tsx`

**Interfaces:**
- Consumes: session permissions and all Task 3/4 API payloads.
- Produces: searchable/filterable/selectable cards, full user drawer, action forms, and sticky bulk controls.

- [ ] Write failing tests for filter/sort query generation, permission-aware buttons, user selection limits, drawer tabs, and action confirmations.
- [ ] Expand TypeScript types and API methods without removing current VIP methods.
- [ ] Refactor the user list into focused components and load detail only when a card opens.
- [ ] Add mobile drawer tabs `Огляд`, `Групи`, `Платежі`, `Історія` with notes/tags in Overview.
- [ ] Add action forms for VIP, XP, block/unblock, roles, notes/tags, and direct messages.
- [ ] Add selection, sticky bulk bar, partial-result display, and refresh after successful mutations.
- [ ] Add blocked, staff-role, payer, and VIP-expiring filters plus all sort options.
- [ ] Preserve safe-area behavior and prevent horizontal overflow on iPhone widths.
- [ ] Run `npm test -- --run`, `npm run typecheck`, and `npm run build`.
- [ ] Commit with `feat: rebuild owner user control interface`.

### Task 6: Blocked Mini App screen and regression coverage

**Files:**
- Modify: `miniapp/src/api/client.ts` or the existing shared API error layer
- Modify: `miniapp/src/App.tsx`
- Create: `miniapp/src/features/access/BlockedAccountPage.tsx`
- Modify: relevant shared styles
- Test: `miniapp/src/App.test.tsx`

**Interfaces:**
- Consumes: backend `403` detail code `ACCOUNT_BLOCKED`.
- Produces: a dedicated blocked-account screen without leaking Owner Control data.

- [ ] Write a failing frontend test for the blocked response.
- [ ] Preserve structured error codes in the shared API client.
- [ ] Render the blocked screen with reason when provided and no retry loop.
- [ ] Run frontend tests, typecheck, and build.
- [ ] Commit with `feat: add blocked account experience`.

### Task 7: Full verification, PR, and merge

**Files:**
- Modify docs only when verification reveals a behavior change.

- [ ] Run `npm test -- --run`, `npm run typecheck`, and `npm run build` in `miniapp`.
- [ ] Run `ruff check .`, `ruff format --check .`, `pytest -q`, and `python -m compileall app`.
- [ ] Run `docker build -t chatpulse-owner-user-control .`.
- [ ] Compare `feature/owner-user-control` against `main` and inspect every changed file.
- [ ] Open a pull request with the feature summary, migration, risk notes, and actual test results.
- [ ] Wait for GitHub checks; inspect and fix every failure on the feature branch.
- [ ] Merge into `main` only after all checks are green and the head SHA is unchanged.
