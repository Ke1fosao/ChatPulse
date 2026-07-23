import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import type { AccountAccess } from "../../api/types";
import { PremiumAnalytics } from "./PremiumAnalytics";

const free: AccountAccess = {
  plan: "free",
  is_owner: false,
  is_vip: false,
  vip_expires_at: null,
  entitlements: [],
};

afterEach(() => cleanup());

it("shows locked extended periods and contextual VIP action", async () => {
  const user = userEvent.setup();
  const onOpenVip = vi.fn();
  render(
    <PremiumAnalytics
      account={free}
      chatId={101}
      trialAvailable
      onOpenVip={onOpenVip}
    />,
  );

  expect(screen.getByText("90 днів")).toBeInTheDocument();
  expect(screen.getByText("6 місяців")).toBeInTheDocument();
  expect(screen.getByText("12 місяців")).toBeInTheDocument();
  expect(screen.getByText("Доступно у VIP")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Відкрити VIP" }));
  expect(onOpenVip).toHaveBeenCalledWith("group_analytics", "analytics.extended_history");
});
