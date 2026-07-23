import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import type { AccountAccess } from "../../api/types";
import { premiumApi } from "../../premium/premiumApi";
import { YearSummaryCard } from "./YearSummaryCard";

vi.mock("../../premium/premiumApi", () => ({
  premiumApi: { yearSummary: vi.fn() },
}));

const free: AccountAccess = {
  plan: "free",
  is_owner: false,
  is_vip: false,
  vip_expires_at: null,
  entitlements: [],
};
const vip: AccountAccess = {
  plan: "vip",
  is_owner: false,
  is_vip: true,
  vip_expires_at: "2026-08-23T10:00:00+00:00",
  entitlements: ["profile.premium_card"],
};

afterEach(() => cleanup());

it("shows a locked yearly preview for free users", async () => {
  const user = userEvent.setup();
  const onOpenVip = vi.fn();
  render(
    <YearSummaryCard account={free} trialAvailable onOpenVip={onOpenVip} />,
  );

  expect(screen.getByText("Мій рік у ChatPulse")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Відкрити VIP" }));
  expect(onOpenVip).toHaveBeenCalledWith("year_summary", "profile.premium_card");
});

it("loads the private yearly summary for VIP", async () => {
  vi.mocked(premiumApi.yearSummary).mockResolvedValue({
    year: 2026,
    messages_count: 40,
    xp_earned: 100,
    active_days: 2,
    groups_count: 1,
    best_streak: 12,
    top_month: 7,
    monthly_xp: [],
    achievements_count: 3,
  });

  render(<YearSummaryCard account={vip} trialAvailable={false} onOpenVip={vi.fn()} />);

  expect(await screen.findByText("40")).toBeInTheDocument();
  expect(screen.getByText("100 XP")).toBeInTheDocument();
  expect(screen.getByText("12 дн.")).toBeInTheDocument();
});
