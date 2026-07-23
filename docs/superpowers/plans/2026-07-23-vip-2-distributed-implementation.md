# ChatPulse VIP 2.0 Distributed Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move premium functionality out of the overloaded VIP page and expose contextual VIP previews, locks, and actions across profile, group analytics, settings, achievements, rankings, and home.

**Architecture:** Keep `AccountAccess` as the verified server-provided access contract. Add reusable frontend premium components and server-side entitlement checks for every premium endpoint. Extend analytics with dedicated premium endpoints rather than weakening the existing free dashboard. Keep `/miniapp/vip` focused on purchase and subscription management only.

**Tech Stack:** FastAPI, SQLAlchemy async, aiogram, React 19, TypeScript, Vite, Vitest, PostgreSQL/Supabase, GitHub Actions.

## Global Constraints

- VIP never grants XP, rank, multiplier, or paid placement.
- Message texts, captions, and files are never stored.
- Owner access is permanent and does not show purchase actions.
- Trial remains one-time: 7 days for 1 Telegram Star.
- Premium enforcement is server-side; frontend locks are explanatory UX only.
- Existing Telegram Mini App initData verification and membership/admin checks remain mandatory.
- AI insights, referrals, and promo codes are excluded.

---

### Task 1: Premium access contract and contextual event tracking

**Files:**
- Modify: `app/services/entitlements.py`
- Create: `app/vip_product_models.py`
- Modify: `app/database.py`
- Create: `app/repositories/vip_product_events.py`
- Create: `app/api/miniapp/premium.py`
- Modify: `app/main.py`
- Create: `supabase/migrations/20260723183000_add_vip_product_events.sql`
- Test: `tests/test_vip_product_events.py`
- Test: `tests/test_premium_routes.py`

**Interfaces:**
- Produces `has_entitlement(account, key) -> bool`.
- Produces `VipProductEventRepository.record(user_id, event_type, source, feature_key, metadata)`.
- Produces `GET /api/miniapp/v1/premium/context` and `POST /api/miniapp/v1/premium/events`.

- [ ] Write repository and API tests proving event validation, source normalization, privacy-safe metadata, and owner/VIP/free context payloads.
- [ ] Run targeted tests and confirm failure because models/routes do not exist.
- [ ] Add the model, additive migration, repository, route, and app wiring.
- [ ] Run targeted tests and full backend tests.
- [ ] Commit as `feat: add premium context and placement events`.

### Task 2: Shared premium frontend primitives

**Files:**
- Create: `miniapp/src/premium/types.ts`
- Create: `miniapp/src/premium/premiumApi.ts`
- Create: `miniapp/src/premium/PremiumContext.tsx`
- Create: `miniapp/src/premium/VipBadge.tsx`
- Create: `miniapp/src/premium/VipUpgradeCard.tsx`
- Create: `miniapp/src/premium/VipGate.tsx`
- Create: `miniapp/src/premium/VipConfirmSheet.tsx`
- Create: `miniapp/src/styles/premium.css`
- Modify: `miniapp/src/main.tsx`
- Test: `miniapp/src/premium/PremiumComponents.test.tsx`

**Interfaces:**
- Produces `usePremium()` with `account`, `trialAvailable`, `has(key)`, and `openVip(source, featureKey)`.
- Produces reusable badge, preview card, gate, and purchase confirmation sheet components.

- [ ] Write failing Vitest tests for free preview, VIP unlocked rendering, owner state, source-preserving navigation, and trial copy.
- [ ] Run targeted frontend test and confirm RED.
- [ ] Implement minimal components and provider.
- [ ] Run targeted tests, typecheck, and build.
- [ ] Commit as `feat: add reusable VIP gates and badges`.

### Task 3: Profile and home premium entry points

**Files:**
- Modify: `miniapp/src/components/ProfileHero.tsx`
- Modify: `miniapp/src/features/profile/ProfilePage.tsx`
- Modify: `miniapp/src/features/home/HomePage.tsx`
- Modify: `miniapp/src/App.tsx`
- Create: `miniapp/src/features/year/YearSummaryCard.tsx`
- Create: `miniapp/src/features/year/YearSummaryPage.tsx`
- Modify: `miniapp/src/api/client.ts`
- Modify: `miniapp/src/api/types.ts`
- Modify: `app/api/miniapp/routes.py`
- Modify: `app/repositories/miniapp.py`
- Test: `miniapp/src/features/profile/ProfileVipEntry.test.tsx`
- Test: `miniapp/src/features/year/YearSummary.test.tsx`
- Test: `tests/test_year_summary.py`

**Interfaces:**
- Produces `GET /api/miniapp/v1/year-summary?year=YYYY`, premium-only.
- Free profile card opens VIP purchase; VIP card opens management; owner opens Owner Panel.

- [ ] Write failing backend and frontend tests for all three account states and locked/unlocked year summary.
- [ ] Confirm RED in CI.
- [ ] Implement profile badge/call-to-action and yearly summary endpoint/page.
- [ ] Verify targeted and full suites.
- [ ] Commit as `feat: distribute VIP entry across profile and home`.

### Task 4: Extended analytics and exports in group dashboard

**Files:**
- Modify: `app/api/miniapp/schemas.py`
- Modify: `app/api/miniapp/routes.py`
- Modify: `app/repositories/miniapp.py`
- Modify: `app/api/billing/routes.py`
- Modify: `miniapp/src/api/types.ts`
- Modify: `miniapp/src/api/client.ts`
- Create: `miniapp/src/features/groups/PremiumAnalytics.tsx`
- Modify: `miniapp/src/features/groups/GroupDashboardPage.tsx`
- Test: `tests/test_premium_analytics.py`
- Test: `miniapp/src/features/groups/PremiumAnalytics.test.tsx`

**Interfaces:**
- Produces `GET /groups/{chat_id}/premium-analytics?period=quarter|half_year|year&compare=...`.
- Free users receive 403 from premium data/export endpoints.
- Group dashboard receives `account` and contextual upgrade navigation.

- [ ] Write failing tests for extended periods, compare math, membership enforcement, entitlement enforcement, and free preview UI.
- [ ] Confirm RED.
- [ ] Implement validated premium repository query and contextual dashboard component.
- [ ] Move CSV/PDF export controls from `/miniapp/vip` into premium analytics.
- [ ] Verify full backend/frontend suites.
- [ ] Commit as `feat: add contextual premium group analytics`.

### Task 5: Premium themes and advanced report controls

**Files:**
- Modify: `app/api/miniapp/schemas.py`
- Modify: `app/api/miniapp/routes.py`
- Modify: `app/models.py`
- Modify: `app/services/entitlements.py`
- Modify: `miniapp/src/api/types.ts`
- Modify: `miniapp/src/features/admin/GroupSettingsPanel.tsx`
- Create: `miniapp/src/premium/PremiumThemeOption.tsx`
- Create: `supabase/migrations/20260723190000_add_advanced_report_settings.sql`
- Test: `tests/test_premium_group_settings.py`
- Test: `miniapp/src/features/admin/PremiumSettings.test.tsx`

**Interfaces:**
- Premium themes are `telegram_wave`, `clean_light`, and new `aurora_gold`; `dark_pulse` remains free.
- Advanced report settings are saved only for group admins with premium access.

- [ ] Write failing tests for premium theme rejection, admin checks, and premium settings UI locks.
- [ ] Confirm RED.
- [ ] Implement schema/model/migration/UI changes.
- [ ] Verify tests and build.
- [ ] Commit as `feat: gate premium themes and report controls`.

### Task 6: Featured achievements in the achievements page

**Files:**
- Modify: `app/api/miniapp/featured.py`
- Modify: `app/repositories/featured_achievements.py`
- Modify: `app/achievement_models.py`
- Modify: `supabase/migrations/20260723150000_add_vip_stars_billing.sql` only if safe; otherwise add a new migration.
- Modify: `miniapp/src/features/achievements/AchievementsPage.tsx`
- Create: `miniapp/src/features/achievements/FeaturedAchievements.tsx`
- Modify: `miniapp/src/App.tsx`
- Test: `tests/test_featured_achievements.py`
- Test: `miniapp/src/features/achievements/FeaturedAchievements.test.tsx`

**Interfaces:**
- VIP/owner can select and reorder up to five earned achievements.
- Free users see five preview slots and an upgrade action.

- [ ] Change tests first from maximum three to maximum five and add ordering tests.
- [ ] Confirm RED.
- [ ] Implement repository, API, and contextual UI changes.
- [ ] Remove achievement loading and controls from standalone VIP route.
- [ ] Verify tests and build.
- [ ] Commit as `feat: move featured achievements into collection`.

### Task 7: Visual VIP identity in rankings

**Files:**
- Modify: `app/repositories/miniapp.py`
- Modify: `miniapp/src/api/types.ts`
- Modify: `miniapp/src/features/rankings/RankingsPage.tsx`
- Modify: `miniapp/src/components/Leaderboard.tsx`
- Test: `tests/test_rankings_vip_badges.py`
- Test: `miniapp/src/features/rankings/RankingVipBadge.test.tsx`

**Interfaces:**
- Ranking rows include `account_plan: free|vip|owner`.
- Sorting and values remain unchanged.

- [ ] Write failing tests showing badges are present but ordering is identical.
- [ ] Confirm RED.
- [ ] Add account plan projection and visual badge rendering.
- [ ] Verify tests.
- [ ] Commit as `feat: show fair visual VIP identity in rankings`.

### Task 8: Simplify VIP purchase and management route

**Files:**
- Modify: `miniapp/src/vip/VipApp.tsx`
- Modify: `miniapp/src/vip/VipApp.test.tsx`
- Modify: `miniapp/src/vip/vipApi.ts`
- Modify: `miniapp/src/telegram/sdk.ts`
- Modify: `miniapp/src/styles/vip.css`

**Interfaces:**
- Route contains plan status, plan cards, Free-vs-VIP comparison, subscription controls, payment history, confirmation sheet, and success state.
- Source query parameter is preserved and returned to after purchase.

- [ ] Rewrite tests first to reject export/achievement controls and require confirmation/success states.
- [ ] Confirm RED.
- [ ] Simplify component and add purchase confirmation/success UX.
- [ ] Verify tests, typecheck, and build.
- [ ] Commit as `refactor: focus VIP route on purchase and management`.

### Task 9: Lifecycle notifications and release verification

**Files:**
- Modify: `app/bot/routers/payments.py`
- Create: `app/services/vip_lifecycle.py`
- Modify: `app/main.py`
- Test: `tests/test_vip_lifecycle.py`
- Modify: `pyproject.toml`
- Modify: `miniapp/package.json`

**Interfaces:**
- Idempotent notifications: purchase, three-day expiry, expiry, cancellation, restoration, renewal problem, refund.
- Release version becomes `0.8.0` consistently.

- [ ] Write failing lifecycle tests using `vip_notifications` as idempotency ledger.
- [ ] Confirm RED.
- [ ] Implement lifecycle service and payment hooks.
- [ ] Run `ruff check .`, `ruff format --check .`, `pytest -q`, `python -m compileall app`, frontend tests, typecheck, Vite build, and Docker build.
- [ ] Open PR, review changed files, fix all CI failures, and squash-merge only when every check is green.
