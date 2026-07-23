import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { openInvoice } from "../telegram/sdk";
import { VipApp } from "./VipApp";
import { vipApi } from "./vipApi";

vi.mock("../telegram/sdk", () => ({
  bindBackButton: vi.fn(() => () => undefined),
  initTelegram: vi.fn(),
  isTelegramContext: vi.fn(() => true),
  notify: vi.fn(),
  openInvoice: vi.fn(),
}));

vi.mock("./vipApi", () => ({
  VipApiError: class VipApiError extends Error {
    constructor(message: string, public readonly status: number) {
      super(message);
    }
  },
  vipApi: {
    plans: vi.fn(),
    history: vi.fn(),
    invoice: vi.fn(),
    subscription: vi.fn(),
  },
}));

const mockedVip = vi.mocked(vipApi);
const mockedOpenInvoice = vi.mocked(openInvoice);

function plansPayload(isVip = false) {
  return {
    account: {
      plan: isVip ? "vip" as const : "free" as const,
      is_owner: false,
      is_vip: isVip,
      vip_expires_at: isVip ? "2026-08-01T12:00:00+00:00" : null,
      entitlements: isVip ? ["premium.all"] : [],
    },
    billing: {
      is_vip: isVip,
      vip_expires_at: isVip ? "2026-08-01T12:00:00+00:00" : null,
      trial_available: !isVip,
      active_subscription: null,
    },
    benefits: ["Розширена аналітика у групах", "Premium-теми та профіль"],
    plans: [
      {
        code: "trial_7d" as const,
        title: "Спробувати VIP",
        short_title: "7 днів",
        description: "Повний VIP на 7 днів.",
        stars: 1,
        duration_days: 7,
        recurring: false,
        badge: "ПЕРШИЙ РАЗ",
        subscription_period: null,
        available: !isVip,
      },
      {
        code: "monthly_30d" as const,
        title: "VIP на місяць",
        short_title: "30 днів",
        description: "Автоматичне продовження.",
        stars: 59,
        duration_days: 30,
        recurring: true,
        badge: "ПОПУЛЯРНИЙ",
        subscription_period: 2592000,
        available: true,
      },
      {
        code: "quarter_90d" as const,
        title: "VIP на 3 місяці",
        short_title: "90 днів",
        description: "Разова покупка.",
        stars: 149,
        duration_days: 90,
        recurring: false,
        badge: "ВИГІДНО",
        subscription_period: null,
        available: true,
      },
      {
        code: "year_365d" as const,
        title: "VIP на рік",
        short_title: "365 днів",
        description: "Разова покупка.",
        stars: 499,
        duration_days: 365,
        recurring: false,
        badge: "НАЙКРАЩА ЦІНА",
        subscription_period: null,
        available: true,
      },
    ],
  };
}

function primeApi() {
  mockedVip.plans.mockResolvedValue(plansPayload());
  mockedVip.history.mockResolvedValue([]);
}

describe("VipApp", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    primeApi();
  });

  afterEach(() => cleanup());

  it("keeps only purchase and management content", async () => {
    render(<VipApp />);

    expect(await screen.findByText("Спробуй VIP за 1 ⭐")).toBeInTheDocument();
    expect(screen.getByText("7 днів")).toBeInTheDocument();
    expect(screen.getByText("30 днів")).toBeInTheDocument();
    expect(screen.getByText("90 днів")).toBeInTheDocument();
    expect(screen.getByText("365 днів")).toBeInTheDocument();
    expect(screen.queryByText("Завантажити аналітику")).not.toBeInTheDocument();
    expect(screen.queryByText("Закріплені досягнення")).not.toBeInTheDocument();
  });

  it("confirms the plan before opening Telegram invoice", async () => {
    const user = userEvent.setup();
    mockedVip.invoice.mockResolvedValue({ invoice_url: "https://t.me/$invoice" });
    mockedOpenInvoice.mockResolvedValue("paid");
    mockedVip.plans
      .mockResolvedValueOnce(plansPayload())
      .mockResolvedValueOnce(plansPayload(true));

    render(<VipApp />);
    await user.click(await screen.findByRole("button", { name: "Спробувати" }));

    expect(screen.getByText("Без автоматичного продовження")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Оплатити 1 ⭐" }));

    await waitFor(() => {
      expect(mockedVip.invoice).toHaveBeenCalledWith("trial_7d");
      expect(mockedOpenInvoice).toHaveBeenCalledWith("https://t.me/$invoice");
      expect(mockedVip.plans).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByText("VIP активовано")).toBeInTheDocument();
  });
});
