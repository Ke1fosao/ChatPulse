# Group Settings UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Побудувати вкладкове Telegram-меню налаштувань групи та окремий autosave admin-flow у Mini App.

**Architecture:** Telegram-меню лишається callback-driven, але розділяється на окремі renderer-и тексту й клавіатур; кожен callback редагує одне повідомлення та повторно перевіряє адміністратора. Mini App використовує існуючий settings API, але відкриває налаштування як окремий екран і зберігає кожне поле одразу з rollback при помилці.

**Tech Stack:** Python 3.12, aiogram 3, FastAPI, React 19, TypeScript, Vitest, pytest.

## Global Constraints

- Доступ до змін мають тільки актуальні Telegram administrator/creator або глобальний owner.
- Telegram settings не створює нових повідомлень після першого `/settings`.
- Mini App повторно перевіряє права на сервері для кожної зміни.
- Нові таблиці та міграції не додаються.
- Усі controls мають українські підписи.

---

### Task 1: Telegram settings presentation

**Files:**
- Modify: `app/bot/keyboards_settings.py`
- Modify: `app/bot/routers/settings.py`
- Test: `tests/test_settings.py`

**Interfaces:**
- Produces: `settings_home_keyboard(settings)`, `reports_keyboard(settings)`, `tracking_keyboard(settings)`, `appearance_keyboard(settings)`, `status_keyboard(settings)`, `danger_keyboard()`.
- Produces callback namespace: `settings:open:<section>`, `settings:back`, `settings:toggle:<field>`, `settings:time:<delta>`, existing reset callbacks.

- [ ] Write failing tests that assert the home keyboard contains five section buttons and every child keyboard contains `settings:back`.
- [ ] Run `pytest tests/test_settings.py -q` and verify failure.
- [ ] Split keyboard builders by section and keep compatibility alias `settings_keyboard = settings_home_keyboard`.
- [ ] Add text renderers for home, reports, tracking, appearance, status and danger sections.
- [ ] Run `pytest tests/test_settings.py -q` and verify pass.
- [ ] Commit `feat: add structured Telegram settings screens`.

### Task 2: Telegram callback navigation and instant changes

**Files:**
- Modify: `app/bot/routers/settings.py`
- Test: `tests/test_settings.py`

**Interfaces:**
- Consumes section keyboard/text functions from Task 1.
- Produces `_render_settings_screen(section, settings)` and `_edit_settings_screen(message, section, settings)`.

- [ ] Write failing router tests for `settings:open:reports`, `settings:back`, toggle refresh in current section and non-admin callback alert.
- [ ] Run the focused tests and verify failure.
- [ ] Implement section routing while preserving one edited message.
- [ ] Implement report-time `-30/+30` minute controls with day wrap and repository update.
- [ ] Keep `/setreporttime` operational as fallback.
- [ ] Run settings tests and verify pass.
- [ ] Commit `feat: add navigable group settings workflow`.

### Task 3: Live admin flags in Mini App

**Files:**
- Modify: `app/api/miniapp/routes.py`
- Modify: `app/repositories/miniapp.py`
- Test: `tests/test_miniapp_api.py`

**Interfaces:**
- Produces `groups[].is_admin` from live `TelegramAccessService.check_admin` when webhook configuration is available.
- Preserves existing PATCH/reset server authorization.

- [ ] Write failing API tests proving list/detail expose admin capability and non-admin PATCH/reset return 403.
- [ ] Run focused pytest and verify failure.
- [ ] Enrich list response with live admin checks without trusting stored member state.
- [ ] Ensure detail capability uses the same helper.
- [ ] Run focused tests and verify pass.
- [ ] Commit `security: expose live group admin capabilities`.

### Task 4: Mini App admin visibility

**Files:**
- Modify: `miniapp/src/components/GroupCard.tsx`
- Modify: `miniapp/src/features/groups/GroupDashboardPage.tsx`
- Modify: `miniapp/src/styles/global.css`
- Test: `miniapp/src/App.test.tsx`

**Interfaces:**
- Produces visible `Ви адміністратор` badge and `Керувати групою` action only when `is_admin` is true.

- [ ] Write failing frontend test for admin and member group cards.
- [ ] Run `npm test -- --run` in `miniapp` and verify failure.
- [ ] Add prominent admin badge/copy to group cards.
- [ ] Replace inline settings toggle with a dedicated settings-screen transition.
- [ ] Run frontend tests and verify pass.
- [ ] Commit `feat: clarify group admin access in mini app`.

### Task 5: Autosave group settings screen

**Files:**
- Modify: `miniapp/src/features/admin/GroupSettingsPanel.tsx`
- Modify: `miniapp/src/features/groups/GroupDashboardPage.tsx`
- Modify: `miniapp/src/styles/global.css`
- Test: `miniapp/src/App.test.tsx`

**Interfaces:**
- Consumes `onSave(settings: Partial<GroupSettings>)`.
- Produces immediate single-field PATCH, pending state per control, success toast and rollback on failure.

- [ ] Write failing tests for autosave success and rollback on rejected API call.
- [ ] Run frontend tests and verify failure.
- [ ] Refactor settings panel into grouped sections and remove global save button.
- [ ] Save only changed field, disable active control and restore server value on error.
- [ ] Add sticky header with back action and admin-only description.
- [ ] Run Vitest, TypeScript and Vite build.
- [ ] Commit `feat: add autosave mini app group settings`.

### Task 6: Verification and merge

**Files:**
- Modify: `README.md` only if command descriptions changed.

- [ ] Run `ruff check .`.
- [ ] Run `ruff format --check .`.
- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall app`.
- [ ] Run `npm test -- --run`, `npm run typecheck`, `npm run build` in `miniapp`.
- [ ] Run `docker build -t chatpulse-group-settings:test .`.
- [ ] Open PR, wait for green CI, squash merge to `main`.
