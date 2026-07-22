import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Achievement, AchievementEventPayload, AchievementRarity } from "../../api/types";
import { AchievementCelebrationLayer } from "./AchievementCelebration";

const mocks = vi.hoisted(() => ({
  achievementEvents: vi.fn(),
  markAchievementSeen: vi.fn(),
  markAchievementShared: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  api: mocks,
}));

vi.mock("../../telegram/sdk", () => ({
  haptic: vi.fn(),
  notify: vi.fn(),
}));

function achievement(
  code: string,
  title: string,
  rarity: AchievementRarity,
): Achievement {
  return {
    code,
    title,
    description: `Опис ${title}`,
    category: "activity",
    rarity,
    scope: "group",
    icon: "trophy",
    visual_theme: `${rarity}_theme`,
    hidden: rarity === "secret",
    important: rarity === "legendary" || rarity === "secret",
    earned: true,
    earned_at: "2026-07-22T10:00:00Z",
    group_title: "ChatPulse Team",
    progress: 100,
    threshold: 100,
    chain: { key: "test", stage: 1, total: 3 },
    reward_xp: 25,
    version: 2,
    season_key: null,
  };
}

function event(
  eventId: number,
  title: string,
  rarity: AchievementRarity,
): AchievementEventPayload {
  return {
    event_id: eventId,
    event_type: "unlock",
    created_at: `2026-07-22T10:00:0${eventId}Z`,
    achievement: achievement(`achievement_${eventId}`, title, rarity),
  };
}

afterEach(cleanup);

beforeEach(() => {
  mocks.achievementEvents.mockReset();
  mocks.markAchievementSeen.mockReset();
  mocks.markAchievementShared.mockReset();
  mocks.markAchievementSeen.mockResolvedValue({ ok: true });
  mocks.markAchievementShared.mockResolvedValue({ ok: true });
});

describe("AchievementCelebrationLayer", () => {
  it("renders a rarity-specific full-screen celebration and acknowledges it", async () => {
    const user = userEvent.setup();
    mocks.achievementEvents.mockResolvedValue([
      event(1, "Номер один", "legendary"),
    ]);

    render(<AchievementCelebrationLayer onOpenCollection={vi.fn()} />);

    expect(await screen.findByText("Номер один")).toBeInTheDocument();
    expect(document.querySelector(".achievement-celebration--legendary")).not.toBeNull();

    await user.click(screen.getByRole("button", { name: "Продовжити" }));

    await waitFor(() => expect(mocks.markAchievementSeen).toHaveBeenCalledWith(1));
    await waitFor(() =>
      expect(screen.queryByText("Номер один")).not.toBeInTheDocument(),
    );
  });

  it("shows at most three individual celebrations before an overflow summary", async () => {
    const user = userEvent.setup();
    mocks.achievementEvents.mockResolvedValue([
      event(1, "Перше", "common"),
      event(2, "Друге", "uncommon"),
      event(3, "Третє", "rare"),
      event(4, "Четверте", "epic"),
    ]);

    render(<AchievementCelebrationLayer onOpenCollection={vi.fn()} />);

    for (const title of ["Перше", "Друге", "Третє"]) {
      expect(await screen.findByText(title)).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Продовжити" }));
    }

    expect(await screen.findByText("Ще 1 нових досягнень")).toBeInTheDocument();
    expect(screen.getByText("Четверте")).toBeInTheDocument();
  });
});
