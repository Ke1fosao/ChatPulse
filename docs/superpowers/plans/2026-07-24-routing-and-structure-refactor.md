# Routing and Structure Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace manual URL checks and oversized orchestration files with explicit frontend routes and smaller feature-focused modules without changing user-facing behavior.

**Architecture:** Add React Router as the single navigation source, keep application bootstrap/data state in focused hooks, and split Owner Control and user-detail UI by responsibility. Backend owner endpoints and repositories will be separated after frontend routing is stable, preserving existing API contracts.

**Tech Stack:** React 19, TypeScript 7, Vite 8, React Router, FastAPI, pytest, Vitest.

## Global Constraints

- Preserve all current Mini App, VIP and Owner Control behavior.
- Keep Telegram authentication and blocked-account handling unchanged.
- Every refactor step must typecheck and build before the next subsystem is changed.
- Do not merge into `main` until CI is green.

---

### Task 1: Frontend routing foundation

**Files:**
- Modify: `miniapp/package.json`
- Modify: `miniapp/src/main.tsx`
- Create: `miniapp/src/routing/RootRouter.tsx`
- Create: `miniapp/src/routing/paths.ts`

- [x] Add `react-router-dom`.
- [x] Replace pathname conditionals with `BrowserRouter` and declarative routes.
- [x] Add centralized route builders for Mini App, VIP and Owner Control URLs.
- [x] Run `npm run typecheck`, `npm test -- --run`, and `npm run build`.
- [x] Commit the routing foundation.

### Task 2: Main Mini App route state

**Files:**
- Modify: `miniapp/src/App.tsx`
- Create: `miniapp/src/routing/AppRoutes.tsx`
- Create: `miniapp/src/hooks/useAppBootstrap.ts`

- [x] Derive active navigation tab from the URL.
- [x] Add routes for home, groups, group details, achievements and profile.
- [x] Move bootstrap loading, Telegram initialization and blocked-account state into `useAppBootstrap`.
- [x] Preserve dialogs, celebration refresh and favorite updates.
- [x] Add route tests and run frontend verification.
- [x] Commit the main Mini App routing refactor.

### Task 3: Owner Control routes and data orchestration

**Files:**
- Modify: `miniapp/src/owner/OwnerApp.tsx`
- Create: `miniapp/src/owner/OwnerLayout.tsx`
- Create: `miniapp/src/owner/OwnerRoutes.tsx`
- Create: `miniapp/src/owner/hooks/useOwnerSession.ts`
- Create: `miniapp/src/owner/hooks/useOwnerNavigation.ts`

- [x] Convert Owner tabs to `/miniapp/owner/*` child routes.
- [x] Add direct user URLs at `/miniapp/owner/users/:telegramId`.
- [x] Keep permission checks and server-side authorization unchanged.
- [x] Add route tests and run frontend verification.
- [x] Commit the Owner routing refactor.

### Task 4: User detail component split

**Files:**
- Modify: `miniapp/src/owner/OwnerUserDrawer.tsx`
- Create focused files under `miniapp/src/owner/users/` and `miniapp/src/owner/users/actions/`.

- [x] Extract header and tab navigation.
- [x] Extract overview, groups, payments and audit tabs.
- [x] Extract VIP, block, XP, role, note, tag and message actions.
- [x] Keep API payloads and confirmations identical.
- [x] Run frontend tests, typecheck and build.
- [x] Commit the user detail split.

### Task 5: Feature-owned styles

**Files:**
- Modify: `miniapp/src/main.tsx`
- Modify feature entry components under `miniapp/src/features/`, `miniapp/src/owner/`, `miniapp/src/premium/` and `miniapp/src/vip/`.

- [x] Leave only global/reset styles in `main.tsx`.
- [x] Import feature styles from their owning feature entry points.
- [x] Verify visual CSS loading for every route in production build.
- [x] Commit style ownership cleanup.

### Task 6: Backend owner route split

**Files:**
- Modify: `app/api/owner/routes.py`
- Create route modules under `app/api/owner/`.
- Modify/add tests under `tests/`.

- [x] Split session, overview, users, groups, payments and audit routers.
- [x] Preserve every existing URL, request schema, response schema and permission dependency.
- [x] Run Ruff, pytest and compileall.
- [x] Commit the backend route split.

### Task 7: User-control repository split

**Files:**
- Modify: `app/repositories/user_control.py`
- Create focused repository modules under `app/repositories/user_control/`.
- Modify service wiring and tests.

- [x] Separate queries, restrictions, staff roles, notes/tags, XP, messaging and audit persistence.
- [x] Keep business rules in services and database operations in repositories.
- [x] Run full backend and Docker verification.
- [x] Commit the repository split.

### Task 8: Final verification and pull request

- [x] Run full frontend and backend checks.
- [x] Compare the branch with `main` for accidental behavior changes.
- [x] Open a pull request with migration notes and verification results.
- [x] Merge only after all CI checks pass.
