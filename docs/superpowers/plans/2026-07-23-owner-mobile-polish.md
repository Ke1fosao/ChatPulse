# Owner Mobile Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Owner Control comfortable on iPhone-sized screens and rebuild the five-item bottom navigation into one stable mobile row.

**Architecture:** Keep existing React components and data flow. Apply mobile-first layout corrections in `owner-mobile.css`, ensure that stylesheet loads after Owner Revenue styles, and preserve tablet/desktop behavior through scoped media queries.

**Tech Stack:** React, TypeScript, CSS, Vite, Vitest, GitHub Actions.

## Global Constraints

- Do not change payment logic or API contracts.
- Keep all five Owner tabs visible in one row.
- Respect iOS safe areas and Telegram viewport variables.
- Avoid horizontal page overflow.
- Run frontend tests, typecheck, build, backend CI, and Docker build before merge.

---

### Task 1: Mobile layout overrides

**Files:**
- Modify: `miniapp/src/styles/owner-mobile.css`

- [ ] Compact top bar and owner identity.
- [ ] Convert page heading and CSV action to a stable mobile layout.
- [ ] Make period filters horizontally scrollable.
- [ ] Make KPI cards readable on narrow screens.
- [ ] Make charts, transaction filters, cards, and drawers responsive.
- [ ] Rebuild bottom navigation as a fixed five-column bar with safe-area support.

### Task 2: Stylesheet order

**Files:**
- Modify: `miniapp/src/main.tsx`

- [ ] Load `owner-mobile.css` after `owner-revenue.css` so mobile overrides win.

### Task 3: Verification

- [ ] Run Vitest.
- [ ] Run TypeScript typecheck.
- [ ] Run Vite production build.
- [ ] Run backend Ruff, pytest, compileall.
- [ ] Run Docker production build.
- [ ] Merge only after all checks pass.
