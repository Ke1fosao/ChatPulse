import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AccountAccess, Achievement } from "../../api/types";
import { FeaturedAchievements } from "./FeaturedAchievements";

const mocks = vi.hoisted(() => ({
  featured: vi.fn(),
  updateFeatured: vi.fn(),
}));

vi.mock("../../vip/vipApi", () => ({
  vipApi: {
    featured: mocks.featured,
    updateFeatured: mocks.updateFeatured,
  },
}));

vi.mock("../../telegram/sdk", () => ({ notify: vi.fn() }));

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
  vip_expires_at: null,
  entitlements: [],
};

function achievement(index: number, secret = false): Achievement {
  return {
    code: `achievement_${index}`,
    title: secret ? "Earned secret" : `Achievement ${index}`,
    description: `Description ${index}`,
    category: secret ? "secret" : "activity",
    rarity: secret ? "secret" : "common",
    scope: "group",
    icon: "message-circle",
    visual_theme: secret ? "secret_glitch" : "blue_pulse",
    hidden: secret,
    important: secret,
    earned: true,
    earned_at: "2026-07-24T10:00:00Z",
    group_title: `Group ${index}`,
    progress: index + 1,
    threshold: index + 1,
    chain: null,
    reward_xp: 5,
    version: 2,
    season_key: null,
    earned_instances: [
      {
        scope_key: `group:${index}`,
        telegram_chat_id: -1000 - index,
        group_title: `Group ${index}`,
        earned_at: "2026-07-24T10:00:00Z",
        progress: index + 1,
      },
    ],
    primary_scope_key: `group:${index}`,
  } as Achievement;
}

afterEach(cleanup);

beforeEach(() => {
  mocks.featured.mockReset();
  mocks.updateFeatured.mockReset();
  mocks.featured.mockResolvedValue([]);
  mocks.updateFeatured.mockImplementation(async (items) =>
    items.map((item: { code: string; scope_key: string }, index: number) => ({
      ...achievement(Number(item.scope_key.split(":")[1])),
      code: item.code,
      scope_key: item.scope_key,
      slot: index + 1,
    })),
  );
});

describe("FeaturedAchievements", () => {
  it("shows five locked profile slots and a contextual upgrade action", async () => {
    const user = userEvent.setup();
    const onOpenVip = vi.fn();
    render(
      <FeaturedAchievements
        account={free}
        achievements={[achievement(1)]}
        trialAvailable
        onOpenVip={onOpenVip}
      />,
    );

    expect(screen.getAllByLabelText("Порожній VIP-слот")).toHaveLength(5);
    await user.click(screen.getByRole("button", { name: "Відкрити VIP" }));
    expect(onOpenVip).toHaveBeenCalledWith(
      "featured_achievements",
      "profile.featured_achievements",
    );
  });

  it("opens a searchable editor with every earned instance and real icons", async () => {
    const user = userEvent.setup();
    const achievements = [
      ...Array.from({ length: 30 }, (_, index) => achievement(index)),
      achievement(99, true),
    ];

    render(
      <FeaturedAchievements
        account={vip}
        achievements={achievements}
        trialAvailable={false}
        onOpenVip={vi.fn()}
      />,
    );

    await user.click(await screen.findByRole("button", { name: "Налаштувати вітрину" }));

    expect(screen.getByText("Achievement 29")).toBeInTheDocument();
    expect(screen.getByText("Earned secret")).toBeInTheDocument();
    expect(screen.queryByText("message-circle")).not.toBeInTheDocument();

    await user.type(screen.getByRole("searchbox", { name: "Пошук нагород" }), "Group 29");
    expect(screen.getByText("Achievement 29")).toBeInTheDocument();
    expect(screen.queryByText("Achievement 1")).not.toBeInTheDocument();
  });

  it("saves concrete group instances in visible slot order", async () => {
    const user = userEvent.setup();

    render(
      <FeaturedAchievements
        account={vip}
        achievements={[achievement(1), achievement(2)]}
        trialAvailable={false}
        onOpenVip={vi.fn()}
      />,
    );

    await user.click(await screen.findByRole("button", { name: "Налаштувати вітрину" }));
    await user.click(screen.getByRole("button", { name: /Achievement 1.*Group 1/ }));
    await user.click(screen.getByRole("button", { name: /Achievement 2.*Group 2/ }));
    await user.click(screen.getByRole("button", { name: "Перемістити Achievement 2 вище" }));
    await user.click(screen.getByRole("button", { name: "Зберегти вітрину" }));

    await waitFor(() =>
      expect(mocks.updateFeatured).toHaveBeenCalledWith([
        { code: "achievement_2", scope_key: "group:2" },
        { code: "achievement_1", scope_key: "group:1" },
      ]),
    );
  });
});
