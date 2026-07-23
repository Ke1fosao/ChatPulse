import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import type { AccountAccess, Achievement } from "../../api/types";
import { FeaturedAchievements } from "./FeaturedAchievements";

const free: AccountAccess = {
  plan: "free",
  is_owner: false,
  is_vip: false,
  vip_expires_at: null,
  entitlements: [],
};

const earned = [{ code: "messages_10", title: "Перше слово", earned: true }] as Achievement[];

afterEach(() => cleanup());

it("shows five locked profile slots and a contextual upgrade action", async () => {
  const user = userEvent.setup();
  const onOpenVip = vi.fn();
  render(
    <FeaturedAchievements
      account={free}
      achievements={earned}
      trialAvailable
      onOpenVip={onOpenVip}
    />,
  );

  expect(screen.getAllByLabelText("Порожній VIP-слот")).toHaveLength(5);
  await user.click(screen.getByRole("button", { name: "Відкрити VIP" }));
  expect(onOpenVip).toHaveBeenCalledWith("featured_achievements", "profile.featured_achievements");
});
