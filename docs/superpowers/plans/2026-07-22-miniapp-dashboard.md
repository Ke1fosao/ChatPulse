# ChatPulse Mini App Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy a premium Telegram Mini App that exposes the user's global ChatPulse profile, all accessible groups, detailed group analytics, rankings, achievements, weekly cards, and admin settings while expanding private-bot functionality.

**Architecture:** Add a React 19 + TypeScript + Vite frontend under `miniapp/`, serve its production build from FastAPI at `/miniapp`, and expose a versioned authenticated API under `/api/miniapp/v1`. Reuse existing SQLAlchemy models and repositories, add a focused Mini App repository/service layer, verify Telegram `initData` on every request, and use Telegram Bot API checks for current group membership and admin writes.

**Tech Stack:** Python 3.12, FastAPI, aiogram 3, SQLAlchemy async, PostgreSQL/Supabase, React 19, TypeScript 5, Vite 7, Vitest, Testing Library, Recharts, Lucide React, CSS Modules, Docker multi-stage builds, GitHub Actions.

## Global Constraints

- The Mini App is hosted by the existing ChatPulse Cloud Run service.
- Production identity comes only from validated Telegram `initData`.
- `auth_date` older than 15 minutes is rejected.
- Message text, captions, and files are never stored or returned.
- A user may read only groups represented by their membership data and confirmed by Telegram when opening sensitive group detail.
- Admin writes require a fresh Telegram `getChatMember` result with status `administrator` or `creator`.
- Existing bot commands and scheduler behavior must remain backward compatible.
- The public API prefix is exactly `/api/miniapp/v1`.
- The static Mini App entry point is exactly `/miniapp`.
- The UI language for v1 is Ukrainian.
- Mobile layouts must support 320px through 480px viewport widths without horizontal scrolling.

---

### Task 1: Telegram Mini App authentication foundation

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/miniapp/__init__.py`
- Create: `app/api/miniapp/auth.py`
- Create: `app/api/miniapp/dependencies.py`
- Create: `app/api/miniapp/schemas.py`
- Test: `tests/test_miniapp_auth.py`

**Interfaces:**
- Produces: `TelegramMiniAppUser`, `validate_init_data(init_data, bot_token, max_age_seconds=900, now=None)`, and `get_miniapp_user` FastAPI dependency.
- Consumes: `Settings.bot_token` and request header `X-Telegram-Init-Data`.

- [ ] **Step 1: Write failing authentication tests**

Cover a valid HMAC payload, tampered `user`, expired `auth_date`, missing header, malformed JSON, and a user ID larger than 32 bits.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `pytest tests/test_miniapp_auth.py -q`

Expected: import failure because `app.api.miniapp.auth` does not exist.

- [ ] **Step 3: Implement canonical Telegram validation**

Use `secret_key = HMAC_SHA256(key="WebAppData", message=bot_token)`, sort all non-`hash` key/value pairs, compare hashes with `hmac.compare_digest`, parse `user`, and enforce a 900-second maximum age.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `pytest tests/test_miniapp_auth.py -q`

Expected: all authentication tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/api tests/test_miniapp_auth.py
git commit -m "feat: validate Telegram Mini App sessions"
```

### Task 2: Mini App repository and read API

**Files:**
- Create: `app/repositories/miniapp.py`
- Create: `app/services/miniapp.py`
- Create: `app/api/miniapp/routes.py`
- Modify: `app/main.py`
- Test: `tests/test_miniapp_repository.py`
- Test: `tests/test_miniapp_api.py`

**Interfaces:**
- Produces: `MiniAppRepository.get_home(user_id)`, `list_groups(user_id)`, `get_group_dashboard(user_id, chat_id, period)`, `get_rankings(user_id, chat_id, metric, period)`, `get_achievements(user_id, chat_id=None)`, and matching FastAPI endpoints.
- Consumes: existing `ActivityRepository`, `GamificationRepository`, SQLAlchemy models, and `TelegramMiniAppUser`.

- [ ] **Step 1: Write failing repository tests**

Create SQLite fixtures with two users and two groups. Verify that the current user sees only their own groups, home totals aggregate all groups, global position is calculated without exposing unrelated profiles, and group metrics return current and previous periods.

- [ ] **Step 2: Verify repository tests fail**

Run: `pytest tests/test_miniapp_repository.py -q`

Expected: import failure for `MiniAppRepository`.

- [ ] **Step 3: Implement read models and serializers**

Return JSON-safe dictionaries with explicit fields: user, global_progress, quick_stats, activity_series, recent_achievements, groups, group overview, personal progress, leaderboard rows, top message metadata, nominations, and admin capability flags.

- [ ] **Step 4: Write and run API tests**

Use dependency overrides for `get_miniapp_user`. Verify `GET /api/miniapp/v1/home`, `/groups`, `/groups/{chat_id}`, `/groups/{chat_id}/rankings`, and `/achievements`; verify unauthorized group IDs return 404 rather than leaking existence.

- [ ] **Step 5: Implement routes and register router**

Register one `APIRouter(prefix="/api/miniapp/v1")` in `create_app` and keep health/webhook endpoints unchanged.

- [ ] **Step 6: Run focused tests**

Run: `pytest tests/test_miniapp_repository.py tests/test_miniapp_api.py -q`

Expected: all read API tests pass.

- [ ] **Step 7: Commit**

```bash
git add app/repositories/miniapp.py app/services/miniapp.py app/api/miniapp/routes.py app/main.py tests/test_miniapp_repository.py tests/test_miniapp_api.py
git commit -m "feat: expose Mini App analytics API"
```

### Task 3: Membership verification and admin API

**Files:**
- Create: `app/services/telegram_access.py`
- Modify: `app/api/miniapp/dependencies.py`
- Modify: `app/api/miniapp/routes.py`
- Modify: `app/repositories/activity.py`
- Test: `tests/test_telegram_access.py`
- Test: `tests/test_miniapp_admin_api.py`

**Interfaces:**
- Produces: `TelegramAccessService.check_member(chat_id, user_id)` and `.check_admin(chat_id, user_id)`, plus PATCH settings and POST reset endpoints.
- Consumes: aiogram `Bot.get_chat_member`, existing group setting serializers, and `ActivityRepository.update_group_setting`.

- [ ] **Step 1: Write failing access-service tests**

Test statuses `creator`, `administrator`, `member`, `restricted`, `left`, and `kicked`, plus Telegram API failure behavior.

- [ ] **Step 2: Implement access service**

Treat `creator`, `administrator`, `member`, and currently active `restricted` users as members. Only `creator` and `administrator` are admins. Fail closed on Bot API errors for sensitive reads and all writes.

- [ ] **Step 3: Write admin API tests**

Verify allowed settings fields, `HH:MM` validation, timezone allowlist, theme allowlist, admin denial, and confirmation phrase required for reset.

- [ ] **Step 4: Implement admin endpoints**

Add `PATCH /groups/{chat_id}/settings` and `POST /groups/{chat_id}/reset`, reuse existing repository logic, and return refreshed settings.

- [ ] **Step 5: Run focused tests**

Run: `pytest tests/test_telegram_access.py tests/test_miniapp_admin_api.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/services/telegram_access.py app/api/miniapp app/repositories/activity.py tests/test_telegram_access.py tests/test_miniapp_admin_api.py
git commit -m "feat: secure Mini App group administration"
```

### Task 4: React Mini App shell and Telegram bridge

**Files:**
- Create: `miniapp/package.json`
- Create: `miniapp/tsconfig.json`
- Create: `miniapp/tsconfig.app.json`
- Create: `miniapp/vite.config.ts`
- Create: `miniapp/index.html`
- Create: `miniapp/src/main.tsx`
- Create: `miniapp/src/App.tsx`
- Create: `miniapp/src/styles/global.css`
- Create: `miniapp/src/telegram/sdk.ts`
- Create: `miniapp/src/api/client.ts`
- Create: `miniapp/src/api/types.ts`
- Create: `miniapp/src/components/AppShell.tsx`
- Create: `miniapp/src/components/BottomNav.tsx`
- Test: `miniapp/src/App.test.tsx`

**Interfaces:**
- Produces: a five-tab responsive application shell and typed `apiClient` that automatically sends `X-Telegram-Init-Data`.
- Consumes: Telegram `window.Telegram.WebApp` and `/api/miniapp/v1`.

- [ ] **Step 1: Add frontend test tooling and failing shell test**

Test that the five Ukrainian navigation labels render and the active tab updates without reloading.

- [ ] **Step 2: Run Vitest and verify RED**

Run: `cd miniapp && npm ci && npm test -- --run`

Expected: missing component/module failures.

- [ ] **Step 3: Implement Telegram bridge and app shell**

Call `ready()`, `expand()`, apply Telegram theme variables, expose haptic helpers, handle Back Button, and show a production-safe "Відкрийте через Telegram" screen when `initData` is absent.

- [ ] **Step 4: Implement premium design tokens**

Use CSS custom properties, dark graphite surfaces, blue-violet accent gradients, accessible contrast, 44px minimum tap targets, safe-area paddings, and reduced-motion support.

- [ ] **Step 5: Run frontend tests and typecheck**

Run: `cd miniapp && npm test -- --run && npm run typecheck`

Expected: tests and TypeScript pass.

- [ ] **Step 6: Commit**

```bash
git add miniapp
git commit -m "feat: scaffold premium Telegram Mini App"
```

### Task 5: Personal home, groups, and group dashboard UI

**Files:**
- Create: `miniapp/src/features/home/HomePage.tsx`
- Create: `miniapp/src/features/groups/GroupsPage.tsx`
- Create: `miniapp/src/features/groups/GroupDashboardPage.tsx`
- Create: `miniapp/src/components/ProfileHero.tsx`
- Create: `miniapp/src/components/StatCard.tsx`
- Create: `miniapp/src/components/ActivityChart.tsx`
- Create: `miniapp/src/components/Heatmap.tsx`
- Create: `miniapp/src/components/GroupCard.tsx`
- Create: `miniapp/src/components/Leaderboard.tsx`
- Create: `miniapp/src/components/EmptyState.tsx`
- Test: `miniapp/src/features/home/HomePage.test.tsx`
- Test: `miniapp/src/features/groups/GroupDashboardPage.test.tsx`

**Interfaces:**
- Produces: data-driven home and group analytics screens with loading, empty, retry, and stale states.
- Consumes: typed home, groups, group-dashboard, comparison, leaderboard, and top-message API responses.

- [ ] **Step 1: Write failing component tests**

Test XP progress, streak/protection cards, activity chart accessible summary, group search/sorting, period switching, leaderboard metric switching, top-message link, and empty states.

- [ ] **Step 2: Implement reusable analytics components**

Keep charts SVG-based or Recharts-based, provide text summaries for accessibility, and never render message text.

- [ ] **Step 3: Implement home and groups flows**

Use skeleton loading, pull-to-refresh compatible reloads, optimistic tab navigation, search, sorting, and Telegram haptic feedback.

- [ ] **Step 4: Implement detailed group dashboard**

Support 7 days, 30 days, and all time; overview comparisons; heatmap; personal progress; rankings; nominations; and message-of-week deep link.

- [ ] **Step 5: Run frontend tests**

Run: `cd miniapp && npm test -- --run`

Expected: all component tests pass.

- [ ] **Step 6: Commit**

```bash
git add miniapp/src
git commit -m "feat: build Mini App analytics experience"
```

### Task 6: Rankings, achievements, profile, reports, and admin UI

**Files:**
- Create: `miniapp/src/features/rankings/RankingsPage.tsx`
- Create: `miniapp/src/features/achievements/AchievementsPage.tsx`
- Create: `miniapp/src/features/profile/ProfilePage.tsx`
- Create: `miniapp/src/features/reports/ReportsPage.tsx`
- Create: `miniapp/src/features/admin/GroupSettingsPanel.tsx`
- Create: `miniapp/src/components/AchievementCard.tsx`
- Create: `miniapp/src/components/ShareCardDialog.tsx`
- Test: `miniapp/src/features/achievements/AchievementsPage.test.tsx`
- Test: `miniapp/src/features/admin/GroupSettingsPanel.test.tsx`

**Interfaces:**
- Produces: complete remaining screens and admin controls.
- Consumes: rankings, achievements, profile-card, weekly-report, and admin endpoints.

- [ ] **Step 1: Write failing tests**

Cover metric filters, achievement rarity/progress, locked achievements, profile sharing, theme selection, exact report time, pause toggles, and reset confirmation.

- [ ] **Step 2: Implement ranking and achievement pages**

Show group context, the user's pinned position, top-three styling, category filters, rarity, unlock date, and progress.

- [ ] **Step 3: Implement profile and report flows**

Support profile-card generation/download/share where Telegram supports it, and show current weekly card plus privacy-safe historical summaries available from stored aggregates.

- [ ] **Step 4: Implement admin settings panel**

Use inline validation, explicit success/error states, admin badge, and destructive confirmation before reset.

- [ ] **Step 5: Run frontend tests and typecheck**

Run: `cd miniapp && npm test -- --run && npm run typecheck`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add miniapp/src
git commit -m "feat: complete Mini App profile and admin tools"
```

### Task 7: Private bot Mini App entry points

**Files:**
- Modify: `app/bot/keyboards.py`
- Modify: `app/bot/routers/private.py`
- Modify: `app/main.py`
- Test: `tests/test_private_miniapp.py`

**Interfaces:**
- Produces: `/open`, `/groups`, `/achievements`, enhanced `/profile`, `/start` Web App button, and Telegram menu button setup.
- Consumes: resolved production Mini App URL `${WEBHOOK_BASE_URL}/miniapp`.

- [ ] **Step 1: Write failing bot tests**

Verify `WebAppInfo` is present, commands produce privacy-safe summaries, and menu setup is skipped when no public base URL exists locally.

- [ ] **Step 2: Implement private commands and buttons**

Keep responses concise and route users to the Mini App for detailed views.

- [ ] **Step 3: Set the bot menu button during startup**

Use `MenuButtonWebApp` without breaking webhook registration.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_private_miniapp.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/bot app/main.py tests/test_private_miniapp.py
git commit -m "feat: open ChatPulse Mini App from private bot"
```

### Task 8: Static hosting, Docker, CI, documentation, and final verification

**Files:**
- Modify: `Dockerfile`
- Modify: `.github/workflows/ci.yml`
- Modify: `.dockerignore`
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: `app/main.py`
- Test: `tests/test_miniapp_static.py`

**Interfaces:**
- Produces: production image containing the Vite bundle, SPA fallback under `/miniapp`, frontend CI, and deployment documentation.
- Consumes: `miniapp/dist` produced by `npm run build`.

- [ ] **Step 1: Write failing static-hosting tests**

Verify `/miniapp`, `/miniapp/`, and nested SPA routes return the index document when assets exist, while missing hashed assets return 404.

- [ ] **Step 2: Implement FastAPI static hosting**

Mount `/miniapp/assets`, return `index.html` for SPA routes, and show a simple unavailable page only when the build directory is absent in local backend-only development.

- [ ] **Step 3: Create multi-stage Docker build**

Build the frontend with Node 22, copy `miniapp/dist` into the Python image, install Python dependencies, and retain the current Cloud Run command.

- [ ] **Step 4: Extend CI**

Install Node 22, run `npm ci`, Vitest, TypeScript, and Vite build before Python Ruff, pytest, and compileall.

- [ ] **Step 5: Update documentation and version**

Document BotFather menu/domain setup, routes, local frontend proxy, production build, privacy, and admin security. Bump ChatPulse to `0.4.0`.

- [ ] **Step 6: Run complete verification**

```bash
cd miniapp && npm ci && npm test -- --run && npm run typecheck && npm run build
cd ..
ruff check .
ruff format --check .
pytest -q
python -m compileall app
```

Expected: every command exits with status 0.

- [ ] **Step 7: Open PR and merge only after green CI**

Create a pull request from `feat/miniapp-dashboard` to `main`, inspect all workflow steps, fix failures, and merge only after the final head SHA has green frontend and backend checks.
