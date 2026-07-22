import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Achievement } from "../../api/types";
import { AchievementsPage } from "./AchievementsPage";

const nearAchievement: Achievement = {
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
  earned: false,
  earned_at: null,
  group_title: null,
  progress: 82,
  threshold: 100,
  chain: { key: "messages", stage: 2, total: 8 },
  reward_xp: 10,
  version: 2,
  season_key: null,
};

const secretAchievement: Achievement = {
  code: "secret_night_owl",
  title: "???",
  description: "Секретне досягнення",
  category: "secret",
  rarity: "secret",
  scope: "group",
  icon: "sparkles",
  visual_theme: "secret_locked",
  hidden: true,
  important: true,
  earned: false,
  earned_at: null,
  group_title: null,
  progress: 0,
  threshold: 0,
  chain: null,
  reward_xp: 35,
  version: 2,
  season_key: null,
};

afterEach(cleanup);

describe("AchievementsPage", () => {
  it("does not reveal the condition or numeric progress of a locked secret", () => {
    render(
      <AchievementsPage
        achievements={[secretAchievement]}
        loading={false}
        onRefresh={vi.fn()}
      />,
    );

    expect(screen.getByText("???")).toBeInTheDocument();
    expect(screen.getByText("Секретне досягнення")).toBeInTheDocument();
    expect(screen.getByText("Умова відкриється після виконання")).toBeInTheDocument();
    expect(screen.queryByText(/0 \/ 0/)).not.toBeInTheDocument();
  });

  it("filters the collection to nearly completed achievements", async () => {
    const user = userEvent.setup();
    render(
      <AchievementsPage
        achievements={[nearAchievement, secretAchievement]}
        loading={false}
        onRefresh={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Фільтри" }));
    await user.click(screen.getByRole("button", { name: "Майже готові" }));

    expect(screen.getByText("Перша сотня")).toBeInTheDocument();
    expect(screen.queryByText("???")).not.toBeInTheDocument();
    expect(screen.getByText("1 результатів")).toBeInTheDocument();
  });
});
