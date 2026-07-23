import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ProfileFeaturedAchievements } from "./ProfileFeaturedAchievements";

const mocks = vi.hoisted(() => ({ featured: vi.fn() }));

vi.mock("../../vip/vipApi", () => ({
  vipApi: { featured: mocks.featured },
}));

beforeEach(() => mocks.featured.mockReset());
afterEach(cleanup);

describe("ProfileFeaturedAchievements", () => {
  it("renders real achievement icons and their source group", async () => {
    mocks.featured.mockResolvedValue([
      {
        code: "messages_100",
        title: "Перша сотня",
        description: "Надіслано 100 повідомлень",
        category: "activity",
        rarity: "uncommon",
        scope: "group",
        icon: "message-circle",
        visual_theme: "green_particles",
        hidden: false,
        important: false,
        earned: true,
        earned_at: "2026-07-24T10:00:00Z",
        group_title: "ChatPulse Team",
        progress: 100,
        threshold: 100,
        chain: { key: "messages", stage: 2, total: 8 },
        reward_xp: 10,
        version: 2,
        season_key: null,
        slot: 1,
        scope_key: "group:-1001",
      },
    ]);

    render(<ProfileFeaturedAchievements onConfigure={vi.fn()} />);

    expect(await screen.findByText("Перша сотня")).toBeInTheDocument();
    expect(screen.getByText("ChatPulse Team")).toBeInTheDocument();
    expect(screen.queryByText("message-circle")).not.toBeInTheDocument();
  });

  it("shows an empty state that opens achievement configuration", async () => {
    const user = userEvent.setup();
    const onConfigure = vi.fn();
    mocks.featured.mockResolvedValue([]);

    render(<ProfileFeaturedAchievements onConfigure={onConfigure} />);

    await user.click(
      await screen.findByRole("button", { name: "Налаштувати вітрину" }),
    );
    expect(onConfigure).toHaveBeenCalledOnce();
  });
});
