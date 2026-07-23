import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { HomePayload } from "../../api/types";
import { usePremium } from "../../premium/PremiumContext";
import { ProfilePage } from "./ProfilePage";

vi.mock("../../premium/PremiumContext", () => ({
  usePremium: vi.fn(),
}));

const mockedPremium = vi.mocked(usePremium);

function payload(plan: "free" | "vip" | "owner"): HomePayload {
  return {
    user: { telegram_id: 1, first_name: "Dmytro", display_name: "Dmytro" },
    account: {
      plan,
      is_owner: plan === "owner",
      is_vip: plan === "vip",
      vip_expires_at: plan === "vip" ? "2026-08-23T10:00:00+00:00" : null,
      entitlements: plan === "free" ? [] : ["premium.all"],
    },
    global_progress: {
      xp_total: 100,
      level: 2,
      tier: "Pulse",
      progress: 10,
      needed: 100,
      rank: 1,
      total_users: 1,
      percentile: 100,
    },
    quick_stats: {
      xp_today: 10,
      current_streak: 2,
      longest_streak: 4,
      protection_left: 3,
      groups_count: 1,
      messages_7d: 30,
    },
    activity_series: [],
    recent_achievements: [],
    groups: [],
  };
}

const emptyAction = () => undefined;

afterEach(() => cleanup());

describe("Profile VIP entry", () => {
  it("turns the free plan card into a contextual one-Star upgrade action", async () => {
    const user = userEvent.setup();
    const openVip = vi.fn();
    mockedPremium.mockReturnValue({
      account: payload("free").account,
      trialAvailable: true,
      loading: false,
      has: () => false,
      refresh: vi.fn(),
      openVip,
    });

    render(
      <ProfilePage
        data={payload("free")}
        onShare={emptyAction}
        onOpenLevels={emptyAction}
        onOpenAchievements={emptyAction}
        onOpenGroups={emptyAction}
      />,
    );

    expect(screen.getByText("7 днів за 1 ⭐")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Відкрий ChatPulse VIP/i }));
    expect(openVip).toHaveBeenCalledWith("profile", "premium.all");
  });

  it("shows a visible VIP badge and management action for active VIP", () => {
    mockedPremium.mockReturnValue({
      account: payload("vip").account,
      trialAvailable: false,
      loading: false,
      has: () => true,
      refresh: vi.fn(),
      openVip: vi.fn(),
    });

    render(
      <ProfilePage
        data={payload("vip")}
        onShare={emptyAction}
        onOpenLevels={emptyAction}
        onOpenAchievements={emptyAction}
        onOpenGroups={emptyAction}
      />,
    );

    expect(screen.getAllByText("VIP").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Керувати ChatPulse VIP/i })).toBeInTheDocument();
  });
});
