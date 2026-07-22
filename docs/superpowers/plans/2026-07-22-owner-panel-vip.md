# ChatPulse Owner Panel + VIP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Побудувати окрему захищену owner-панель усередині ChatPulse Mini App і централізовану VIP-роль, яку може видавати лише власник.

**Architecture:** FastAPI отримує окремий router `/api/owner/v1` з dependency, що перевіряє Telegram HMAC та singleton owner ID на кожному запиті. VIP і аудит зберігаються в окремих таблицях, а звичайний Mini App отримує account/entitlement payload через централізований сервіс. React bundle визначає `/miniapp/owner` і монтує окремий `OwnerApp`.

**Tech Stack:** Python 3.12, FastAPI, async SQLAlchemy, PostgreSQL/Supabase, React 19, TypeScript, Vite, Vitest, pytest.

## Global Constraints

- Власник визначається лише за перевіреним Telegram ID у `bot_owner`.
- VIP не отримує owner або group-admin прав.
- Усі owner mutations мають audit log.
- Не зберігати тексти повідомлень, captions чи файли.
- Небезпечні дії потребують explicit confirmation.
- Owner UI — окремий маршрут `/miniapp/owner` у тому самому bundle.

---

### Task 1: Owner authorization contract

**Files:**
- Create: `app/api/owner/__init__.py`
- Create: `app/api/owner/dependencies.py`
- Create: `tests/test_owner_panel_auth.py`

**Interfaces:**
- Consumes: `get_miniapp_user`, `OwnerRepository.is_owner()`.
- Produces: `get_owner_user(request, user) -> TelegramMiniAppUser`.

- [ ] Write tests proving missing Telegram auth returns 401, non-owner returns 403, owner passes, and VIP alone does not pass.
- [ ] Run `pytest tests/test_owner_panel_auth.py -q` and confirm RED.
- [ ] Implement the owner dependency with no client-supplied role fields.
- [ ] Run focused tests and confirm GREEN.

### Task 2: VIP persistence, entitlement service, and audit

**Files:**
- Modify: `app/models.py`
- Modify: `app/repositories/owner.py`
- Create: `app/repositories/owner_panel.py`
- Create: `app/services/entitlements.py`
- Create: `supabase/migrations/20260722110000_add_owner_panel_vip.sql`
- Create: `tests/test_entitlements.py`
- Create: `tests/test_owner_panel_repository.py`

**Interfaces:**
- Produces: `AccountAccess`, `PREMIUM_ENTITLEMENTS`, `OwnerPanelRepository.grant_vip()`, `revoke_vip()`, `get_account_access()`, `record_audit()`.

- [ ] Write repository and service tests for free, active VIP, expired VIP, owner, permanent grant, timed grant, revoke, owner-target rejection, and audit persistence.
- [ ] Run focused tests and confirm RED.
- [ ] Add `VipGrant` and `OwnerAuditLog` models plus SQL migration with indexes, constraints, RLS, and no public policies.
- [ ] Implement repository/service methods with server-derived owner ID and UTC expiry checks.
- [ ] Run focused tests and confirm GREEN.

### Task 3: Owner API

**Files:**
- Create: `app/api/owner/schemas.py`
- Create: `app/api/owner/routes.py`
- Modify: `app/main.py`
- Create: `tests/test_owner_panel_api.py`

**Interfaces:**
- Produces endpoints under `/api/owner/v1`: session, overview, users, user detail, grant/revoke VIP, groups, group patch, audit.

- [ ] Write API tests for protected reads, pagination/search, timed/permanent VIP, confirmation validation, owner-target rejection, group controls, and audit response.
- [ ] Run `pytest tests/test_owner_panel_api.py -q` and confirm RED.
- [ ] Implement schemas, routes, app-state repository wiring, and router registration.
- [ ] Run focused tests and confirm GREEN.

### Task 4: Regular Mini App account payload

**Files:**
- Modify: `app/api/miniapp/routes.py`
- Modify: `app/repositories/miniapp.py`
- Modify: `miniapp/src/api/types.ts`
- Modify: `tests/test_miniapp_api.py`

**Interfaces:**
- Extends `GET /api/miniapp/v1/home` with `account: {plan,is_owner,is_vip,vip_expires_at,entitlements}`.

- [ ] Write backend tests for free/VIP/owner account payload.
- [ ] Run focused tests and confirm RED.
- [ ] Inject entitlement resolution without trusting frontend flags.
- [ ] Run focused tests and confirm GREEN.

### Task 5: Owner Mini App frontend

**Files:**
- Create: `miniapp/src/owner/OwnerApp.tsx`
- Create: `miniapp/src/owner/OwnerShell.tsx`
- Create: `miniapp/src/owner/OwnerOverview.tsx`
- Create: `miniapp/src/owner/OwnerUsers.tsx`
- Create: `miniapp/src/owner/OwnerGroups.tsx`
- Create: `miniapp/src/owner/OwnerAudit.tsx`
- Create: `miniapp/src/owner/ownerApi.ts`
- Create: `miniapp/src/owner/types.ts`
- Modify: `miniapp/src/main.tsx`
- Modify: `miniapp/src/features/profile/ProfilePage.tsx`
- Modify: `miniapp/src/styles/global.css`
- Create: `miniapp/src/owner/OwnerApp.test.tsx`

**Interfaces:**
- `/miniapp/owner` mounts `OwnerApp`.
- The normal profile shows the owner-entry control only when `home.account.is_owner`.

- [ ] Write Vitest tests for route mounting, 403 closed screen, overview rendering, VIP grant/revoke request payloads, and owner-only entry visibility.
- [ ] Run `cd miniapp && npm test -- --run` and confirm RED.
- [ ] Implement responsive owner UI and API client.
- [ ] Run tests, typecheck, and build until GREEN.

### Task 6: Documentation and release verification

**Files:**
- Modify: `README.md`
- Modify: `app/main.py`
- Modify: `miniapp/package.json`
- Modify: `tests/test_health.py`

- [ ] Document owner route, VIP semantics, security boundary, entitlement checks, and migration.
- [ ] Bump backend/frontend version to `0.5.0`.
- [ ] Run `ruff check .`, `ruff format --check .`, `pytest -q`, `python -m compileall app`.
- [ ] Run `cd miniapp && npm test -- --run && npm run typecheck && npm run build`.
- [ ] Open PR, inspect CI, fix failures, and merge only after all checks are green.
