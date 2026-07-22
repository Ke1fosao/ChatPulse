import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OwnerApp } from "./OwnerApp";
import { ownerApi } from "./ownerApi";

vi.mock("./ownerApi", () => ({
  ownerApi: {
    session: vi.fn(),
    overview: vi.fn(),
    users: vi.fn(),
    groups: vi.fn(),
    audit: vi.fn(),
    grantVip: vi.fn(),
    revokeVip: vi.fn(),
    updateGroup: vi.fn(),
  },
}));

const mockedApi = vi.mocked(ownerApi);

function primeOwnerApi() {
  mockedApi.session.mockResolvedValue({
    owner: { telegram_id: 101, display_name: "Dmytro", username: "veheblya" },
    account: {
      plan: "owner",
      is_owner: true,
      is_vip: false,
      vip_expires_at: null,
      entitlements: ["premium.all"],
    },
  });
  mockedApi.overview.mockResolvedValue({
    users_total: 12,
    groups_total: 3,
    active_groups: 2,
    vip_total: 1,
    messages_7d: 450,
  });
  mockedApi.users.mockResolvedValue({
    total: 1,
    items: [
      {
        telegram_id: 202,
        display_name: "VIP Client",
        username: "client",
        global_xp_total: 120,
        groups_count: 1,
        is_vip: false,
        vip_expires_at: null,
        last_activity_at: "2026-07-22T09:00:00Z",
      },
    ],
  });
  mockedApi.groups.mockResolvedValue({ items: [], total: 0 });
  mockedApi.audit.mockResolvedValue({ items: [] });
  mockedApi.grantVip.mockResolvedValue({
    telegram_user_id: 202,
    is_active: true,
    expires_at: null,
  });
}

describe("OwnerApp", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    primeOwnerApi();
  });

  it("renders the isolated owner dashboard after server authorization", async () => {
    render(<OwnerApp />);

    expect(await screen.findByText("Owner Control")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Користувачі" })).toBeInTheDocument();
  });

  it("shows a closed screen when the server rejects owner access", async () => {
    mockedApi.session.mockRejectedValueOnce(Object.assign(new Error("Доступ заборонено"), { status: 403 }));

    render(<OwnerApp />);

    expect(await screen.findByText("Owner Panel закрито")).toBeInTheDocument();
  });

  it("grants VIP only after explicit confirmation", async () => {
    const user = userEvent.setup();
    render(<OwnerApp />);
    await screen.findByText("Owner Control");

    await user.click(screen.getByRole("button", { name: "Користувачі" }));
    await user.click(await screen.findByRole("button", { name: "Керувати VIP для VIP Client" }));
    await user.type(screen.getByLabelText("Причина"), "Партнерський клієнт");
    await user.click(screen.getByRole("button", { name: "Видати VIP" }));

    expect(mockedApi.grantVip).toHaveBeenCalledWith(202, {
      mode: "permanent",
      reason: "Партнерський клієнт",
      confirmation: "ВИДАТИ VIP",
    });
  });
});
