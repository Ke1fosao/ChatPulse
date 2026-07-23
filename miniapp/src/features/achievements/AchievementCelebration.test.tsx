import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type {
  Achievement,
  AchievementEventPayload,
  AchievementRarity,
} from "../../api/types";
import { AchievementCelebrationLayer } from "./AchievementCelebration";

const mocks = vi.hoisted(() => ({
  achievementEvents: vi.fn(),
  achievementCard: vi.fn(),
  markAchievementSeen: vi.fn(),
  markAchievementShared: vi.fn(),
  downloadBlob: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  api: {
    achievementEvents: mocks.achievementEvents,
    achievementCard: mocks.achievementCard,
    markAchievementSeen: mocks.markAchievementSeen,
    markAchievementShared: mocks.markAchievementShared,
  },
  downloadBlob: mocks.downloadBlob,
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
    earned_instances: [
      {
        scope_key: "group:-1001",
        telegram_chat_id: -1001,
        group_title: "ChatPulse Team",
        earned_at: "2026-07-22T10:00:00Z",
        progress: 100,
      },
    ],
    primary_scope_key: "group:-1001",
  } as Achievement;
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
  mocks.achievementCard.mockReset();
  mocks.markAchievementSeen.mockReset();
  mocks.markAchievementShared.mockReset();
  mocks.downloadBlob.mockReset();
  mocks.achievementCard.mockResolvedValue(new Blob(["png"], { type: "image/png" }));
  mocks.markAchievementSeen.mockResolvedValue({ ok: true });
  mocks.markAchievementShared.mockResolvedValue({ ok: true });
});

describe("AchievementCelebrationLayer", () => {
  it.each([
    ["common", "toast"],
    ["uncommon", "toast"],
    ["rare", "modal"],
    ["epic", "modal"],
    ["legendary", "fullscreen"],
    ["secret", "fullscreen"],
  ] as const)("renders %s unlocks in %s mode", async (rarity, mode) => {
    mocks.achievementEvents.mockResolvedValue([event(1, `Mode ${rarity}`, rarity)]);

    render(<AchievementCelebrationLayer onOpenCollection={vi.fn()} />);

    expect(await screen.findByText(`Mode ${rarity}`)).toBeInTheDocument();
    expect(
      document.querySelector(`.achievement-celebration--${mode}`),
    ).not.toBeNull();
    expect(screen.getByText("+25 XP")).toBeInTheDocument();
  });

  it("acknowledges a legendary celebration", async () => {
    const user = userEvent.setup();
    mocks.achievementEvents.mockResolvedValue([event(1, "Номер один", "legendary")]);

    render(<AchievementCelebrationLayer onOpenCollection={vi.fn()} />);

    expect(await screen.findByText("Номер один")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Продовжити" }));

    await waitFor(() => expect(mocks.markAchievementSeen).toHaveBeenCalledWith(1));
    await waitFor(() =>
      expect(screen.queryByText("Номер один")).not.toBeInTheDocument(),
    );
  });

  it("fetches and downloads a trusted PNG when file sharing is unavailable", async () => {
    const user = userEvent.setup();
    mocks.achievementEvents.mockResolvedValue([
      event(7, "Перша сотня", "uncommon"),
    ]);

    render(<AchievementCelebrationLayer onOpenCollection={vi.fn()} />);

    expect(await screen.findByText("Перша сотня")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Поділитися" }));

    await waitFor(() => expect(mocks.achievementCard).toHaveBeenCalledWith(7));
    expect(mocks.downloadBlob).toHaveBeenCalledWith(
      expect.any(Blob),
      "chatpulse-achievement_7.png",
    );
    expect(mocks.markAchievementShared).toHaveBeenCalledWith(7);
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
