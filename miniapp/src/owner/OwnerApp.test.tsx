import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { OwnerApp } from "./OwnerApp";
import { ownerApi } from "./ownerApi";

vi.mock("./ownerApi", () => ({
  OwnerApiError: class OwnerApiError extends Error {
    constructor(message: string, public readonly status: number, public readonly code?: string) {
      super(message);
    }
  },
  ownerApi: {
    session: vi.fn(),
    overview: vi.fn(),
    users: vi.fn(),
    userDetail: vi.fn(),
    groups: vi.fn(),
    audit: vi.fn(),
    grantVip: vi.fn(),
    revokeVip: vi.fn(),
    blockUser: vi.fn(),
    unblockUser: vi.fn(),
    saveNote: vi.fn(),
    addTag: vi.fn(),
    removeTag: vi.fn(),
    adjustXp: vi.fn(),
    setRole: vi.fn(),
    removeRole: vi.fn(),
    messageUser: vi.fn(),
    bulkUsers: vi.fn(),
    updateGroup: vi.fn(),
  },
}));

const mockedApi = vi.mocked(ownerApi);

function renderOwnerApp() {
  return render(
    <MemoryRouter initialEntries={["/miniapp/owner"]}>
      <Routes>
        <Route path="/miniapp/owner/*" element={<OwnerApp />} />
      </Routes>
    </MemoryRouter>,
  );
}

function primeOwnerApi() {
  mockedApi.session.mockResolvedValue({
    owner: { telegram_id: 101, display_name: "Dmytro", username: "veheblya" },
    actor: {
      telegram_user_id: 101,
      role: "owner",
      is_owner: true,
      permissions: [
        "users.view", "audit.view", "vip.manage", "xp.manage", "users.block",
        "users.notes", "users.message", "bulk.vip", "bulk.block",
        "bulk.tag_message", "staff.manage",
      ],
    },
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
    limit: 50,
    offset: 0,
    items: [{
      telegram_id: 202,
      display_name: "VIP Client",
      username: "client",
      global_xp_total: 120,
      global_level: 2,
      groups_count: 1,
      is_vip: false,
      vip_expires_at: null,
      is_blocked: false,
      role: null,
      payment_count: 1,
      stars_total: 150,
      last_payment_at: "2026-07-22T08:00:00Z",
      created_at: "2026-07-20T08:00:00Z",
      last_activity_at: "2026-07-22T09:00:00Z",
    }],
  });
  mockedApi.userDetail.mockResolvedValue({
    telegram_id: 202,
    display_name: "VIP Client",
    username: "client",
    language_code: "uk",
    created_at: "2026-07-20T08:00:00Z",
    last_activity_at: "2026-07-22T09:00:00Z",
    global_xp_total: 120,
    global_level: 2,
    is_owner: false,
    role: null,
    is_blocked: false,
    restriction: null,
    vip: { is_active: false, source: null, starts_at: null, expires_at: null },
    payment_summary: {
      stars_total: 150,
      payment_count: 1,
      last_payment_at: "2026-07-22T08:00:00Z",
      active_subscription: false,
    },
    note: "Тестовий клієнт",
    tags: ["тестер"],
    groups: [{
      telegram_chat_id: -1001,
      title: "Test Group",
      username: null,
      xp_total: 120,
      level: 2,
      last_seen_at: "2026-07-22T09:00:00Z",
    }],
    adjustments: [],
    deliveries: [],
    audit: [],
  });
  mockedApi.groups.mockResolvedValue({ items: [], total: 0 });
  mockedApi.audit.mockResolvedValue({ items: [] });
}

describe("OwnerApp", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    primeOwnerApi();
  });

  afterEach(() => cleanup());

  it("renders the isolated owner dashboard after server authorization", async () => {
    renderOwnerApp();
    expect(await screen.findByText("Головний огляд")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Користувачі" })).toBeInTheDocument();
  });

  it("shows a closed screen when the server rejects admin access", async () => {
    mockedApi.session.mockRejectedValueOnce(Object.assign(new Error("Доступ заборонено"), { status: 403 }));
    renderOwnerApp();
    expect(await screen.findByText("Owner Panel закрито")).toBeInTheDocument();
  });

  it("opens the complete user card from the users list", async () => {
    const user = userEvent.setup();
    renderOwnerApp();
    await screen.findByText("Головний огляд");
    await user.click(screen.getByRole("button", { name: "Користувачі" }));
    await user.click(await screen.findByRole("button", { name: "Відкрити картку VIP Client" }));
    expect(await screen.findByRole("dialog", { name: "Картка користувача" })).toBeInTheDocument();
    expect(await screen.findByText("Тестовий клієнт")).toBeInTheDocument();
    expect(mockedApi.userDetail).toHaveBeenCalledWith(202);
  });

  it("shows only the users workspace to support staff", async () => {
    mockedApi.session.mockResolvedValueOnce({
      owner: { telegram_id: 303, display_name: "Support", username: "support" },
      actor: {
        telegram_user_id: 303,
        role: "support",
        is_owner: false,
        permissions: ["users.view", "users.notes", "users.message"],
      },
      account: {
        plan: "free",
        is_owner: false,
        is_vip: false,
        vip_expires_at: null,
        entitlements: [],
      },
    });
    renderOwnerApp();
    expect(await screen.findByRole("heading", { name: "Користувачі" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Огляд" })).not.toBeInTheDocument();
    expect(screen.getByText("SUPPORT")).toBeInTheDocument();
  });
});
