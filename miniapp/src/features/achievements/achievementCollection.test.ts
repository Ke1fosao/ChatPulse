import { describe, expect, it } from "vitest";
import type { Achievement } from "../../api/types";
import { buildAchievementCollection } from "./achievementCollection";

function achievement(
  code: string,
  stage: number,
  threshold: number,
  progress: number,
  earned: boolean,
): Achievement {
  return {
    code,
    title: `Messages ${threshold}`,
    description: `Send ${threshold} messages`,
    category: "activity",
    rarity: stage >= 3 ? "rare" : "common",
    scope: "group",
    icon: "message-circle",
    visual_theme: "blue_pulse",
    hidden: false,
    important: false,
    earned,
    earned_at: earned ? "2026-07-24T10:00:00Z" : null,
    group_title: earned ? "Team" : null,
    progress,
    threshold,
    chain: { key: "messages", stage, total: 3 },
    reward_xp: stage * 5,
    version: 2,
    season_key: null,
  };
}

describe("buildAchievementCollection", () => {
  it("groups a progression chain into one collection item", () => {
    const items = buildAchievementCollection([
      achievement("messages_10", 1, 10, 10, true),
      achievement("messages_100", 2, 100, 100, true),
      achievement("messages_500", 3, 500, 240, false),
    ]);

    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({
      kind: "chain",
      key: "chain:messages",
      completedStages: 2,
      totalStages: 3,
      currentProgress: 240,
    });
    if (items[0].kind === "chain") {
      expect(items[0].nextAchievement?.code).toBe("messages_500");
      expect(items[0].stages.map((item) => item.code)).toEqual([
        "messages_10",
        "messages_100",
        "messages_500",
      ]);
    }
  });

  it("keeps standalone achievements separate", () => {
    const standalone = {
      ...achievement("secret_signal", 1, 1, 1, true),
      chain: null,
      hidden: true,
      rarity: "secret" as const,
    };

    const items = buildAchievementCollection([standalone]);

    expect(items).toEqual([
      expect.objectContaining({ kind: "achievement", key: "achievement:secret_signal" }),
    ]);
  });
});
