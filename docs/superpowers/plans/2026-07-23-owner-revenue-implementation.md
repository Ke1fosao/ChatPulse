# ChatPulse Owner Revenue 0.9.0 Implementation Plan

**Goal:** Add a protected payments workspace to Owner Panel with Stars KPIs, revenue timeline, trial conversion, searchable transactions, CSV export, private notes, subscription controls and safe refunds.

## Safety constraints

- Every route uses the existing immutable-Telegram-ID owner dependency.
- Financial data is server-only and never exposed through Supabase client policies.
- Refunds are limited to the latest active paid entitlement and are blocked when a later purchase or owner grant exists.
- Telegram side effects happen before local state mutation.
- Every mutation is written to the owner audit log.
- No fiat accounting, tax calculations, referrals or AI.

## Tasks

- [ ] Add private owner payment-note model and RLS migration.
- [ ] Add `OwnerRevenueRepository` for summary, timeline, funnel, transactions, details, notes and CSV.
- [ ] Add `OwnerPaymentService` for refund and subscription mutations.
- [ ] Add owner payment API routes and validation schemas.
- [ ] Add tests for KPIs, conversion, filters, notes, safe refund and owner-only routes.
- [ ] Add Owner Panel `Оплати` tab, KPI cards, timeline, plan distribution and transaction list.
- [ ] Add transaction drawer with note, refund and subscription controls.
- [ ] Add CSV download with active filters.
- [ ] Bump backend/frontend/health version to 0.9.0.
- [ ] Run Ruff, pytest, compileall, Vitest, typecheck, Vite build and Docker build.
- [ ] Apply additive migration, verify RLS, update PR and squash-merge only when green.
