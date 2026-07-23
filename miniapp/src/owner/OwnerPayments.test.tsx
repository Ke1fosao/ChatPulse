import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { revenueApi } from "./revenueApi";
import { OwnerPayments } from "./OwnerPayments";

vi.mock("./revenueApi", () => ({
  revenueApi: {
    summary: vi.fn(),
    timeline: vi.fn(),
    plans: vi.fn(),
    transactions: vi.fn(),
    detail: vi.fn(),
    exportCsv: vi.fn(),
  },
}));

const mockedApi = vi.mocked(revenueApi);

afterEach(() => cleanup());

beforeEach(() => {
  vi.clearAllMocks();
  mockedApi.summary.mockResolvedValue({
    period_days: 30,
    stars: 208,
    payments: 4,
    unique_payers: 3,
    average_payment: 52,
    arppu_stars: 69.33,
    active_paid_vip: 2,
    active_gifted_vip: 1,
    active_subscriptions: 1,
    mrr_stars: 59,
    refunds: 1,
    refunded_stars: 1,
    expiring_7d: 1,
    trial_paid: 2,
    trial_converted: 1,
    trial_conversion_percent: 50,
  });
  mockedApi.timeline.mockResolvedValue([{ date: "2026-07-23", gross_stars: 59, refunded_stars: 0, net_stars: 59, payments: 1 }]);
  mockedApi.plans.mockResolvedValue([{ product_code: "monthly_30d", payments: 1, stars: 59 }]);
  mockedApi.transactions.mockResolvedValue({
    total: 1,
    items: [{
      id: 11,
      telegram_user_id: 20,
      display_name: "Monthly User",
      username: "monthly",
      product_code: "monthly_30d",
      stars_amount: 59,
      status: "paid",
      is_recurring: true,
      is_first_recurring: true,
      paid_at: "2026-07-23T10:00:00+00:00",
      granted_until: "2026-08-22T10:00:00+00:00",
      telegram_payment_charge_id: "charge-11",
    }],
  });
});

it("renders Stars KPIs, funnel and transaction list", async () => {
  render(<OwnerPayments />);

  expect(await screen.findByText("208 ⭐")).toBeInTheDocument();
  expect(screen.getByText("59 ⭐")).toBeInTheDocument();
  expect(screen.getByText("50%")).toBeInTheDocument();
  expect(screen.getByText("Monthly User")).toBeInTheDocument();
  expect(screen.getByText("Оплати та підписки")).toBeInTheDocument();
});
