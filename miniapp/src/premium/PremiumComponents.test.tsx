import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AccountAccess } from "../api/types";
import { VipBadge } from "./VipBadge";
import { VipGate } from "./VipGate";
import { VipUpgradeCard } from "./VipUpgradeCard";

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
  entitlements: ["analytics.extended_history", "premium.all"],
};

const owner: AccountAccess = {
  plan: "owner",
  is_owner: true,
  is_vip: false,
  vip_expires_at: null,
  entitlements: ["premium.all"],
};

afterEach(() => cleanup());

describe("premium components", () => {
  it("renders VIP and OWNER identity without changing free identity", () => {
    const { rerender } = render(<VipBadge account={vip} />);
    expect(screen.getByText("VIP")).toBeInTheDocument();

    rerender(<VipBadge account={owner} />);
    expect(screen.getByText("OWNER")).toBeInTheDocument();

    rerender(<VipBadge account={free} />);
    expect(screen.queryByText("VIP")).not.toBeInTheDocument();
  });

  it("shows a useful preview and one-Star trial call to action", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(
      <VipUpgradeCard
        title="Розширена аналітика"
        description="Порівнюй 90, 180 і 365 днів."
        source="group_analytics"
        featureKey="analytics.extended_history"
        trialAvailable
        onOpen={onOpen}
      />,
    );

    expect(screen.getByText("Доступно у VIP")).toBeInTheDocument();
    expect(screen.getByText("7 днів за 1 ⭐")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Відкрити VIP" }));
    expect(onOpen).toHaveBeenCalledWith("group_analytics", "analytics.extended_history");
  });

  it("unlocks children only when entitlement is present", () => {
    const { rerender } = render(
      <VipGate
        account={free}
        entitlement="analytics.extended_history"
        preview={<div>Locked preview</div>}
      >
        <div>Premium content</div>
      </VipGate>,
    );
    expect(screen.getByText("Locked preview")).toBeInTheDocument();
    expect(screen.queryByText("Premium content")).not.toBeInTheDocument();

    rerender(
      <VipGate
        account={vip}
        entitlement="analytics.extended_history"
        preview={<div>Locked preview</div>}
      >
        <div>Premium content</div>
      </VipGate>,
    );
    expect(screen.getByText("Premium content")).toBeInTheDocument();
  });
});
