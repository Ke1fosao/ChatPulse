import { getInitData } from "../telegram/sdk";
import type {
  BulkActionPayload,
  BulkActionResult,
  OwnerAuditPayload,
  OwnerGroup,
  OwnerGroupsPayload,
  OwnerOverviewData,
  OwnerSession,
  OwnerUserDetail,
  OwnerUserFilters,
  OwnerUsersPayload,
  StaffRole,
  VipFilter,
  VipGrantPayload,
  VipMutationResult,
  VipRevokePayload,
} from "./types";

export class OwnerApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
    public readonly detail?: unknown,
  ) {
    super(message);
  }
}

function headers(init?: RequestInit): Headers {
  const result = new Headers(init?.headers);
  result.set("Accept", "application/json");
  const initData = getInitData();
  if (initData) result.set("X-Telegram-Init-Data", initData);
  if (init?.body) result.set("Content-Type", "application/json");
  return result;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/owner/v1${path}`, {
    ...init,
    headers: headers(init),
  });
  if (!response.ok) {
    let message = "Не вдалося виконати owner-запит.";
    let code: string | undefined;
    let detail: unknown;
    try {
      const body = (await response.json()) as { detail?: string | Record<string, unknown> };
      detail = body.detail;
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (body.detail && typeof body.detail === "object") {
        code = typeof body.detail.code === "string" ? body.detail.code : undefined;
        message = typeof body.detail.message === "string" ? body.detail.message : message;
      }
    } catch {
      // Keep the safe fallback when the server did not return JSON.
    }
    throw new OwnerApiError(message, response.status, code, detail);
  }
  return (await response.json()) as T;
}

const defaultUserFilters: OwnerUserFilters = {
  query: "",
  vip: "all",
  status: "all",
  role: "all",
  payment: "all",
  tag: "",
  sort: "activity_desc",
  limit: 50,
  offset: 0,
};

export const ownerApi = {
  session: () => request<OwnerSession>("/session"),
  overview: () => request<OwnerOverviewData>("/overview"),
  users: (
    filtersOrQuery: OwnerUserFilters | string = defaultUserFilters,
    vip: VipFilter = "all",
    limit = 50,
    offset = 0,
  ) => {
    const filters = typeof filtersOrQuery === "string"
      ? { ...defaultUserFilters, query: filtersOrQuery, vip, limit, offset }
      : filtersOrQuery;
    const params = new URLSearchParams({
      vip: filters.vip,
      account_status: filters.status,
      role: filters.role,
      payment: filters.payment,
      sort: filters.sort,
      limit: String(filters.limit),
      offset: String(filters.offset),
    });
    if (filters.query.trim()) params.set("q", filters.query.trim());
    if (filters.tag.trim()) params.set("tag", filters.tag.trim());
    return request<OwnerUsersPayload>(`/users?${params.toString()}`);
  },
  userDetail: (userId: number) => request<OwnerUserDetail>(`/users/${userId}`),
  groups: (query = "", limit = 50, offset = 0) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (query.trim()) params.set("q", query.trim());
    return request<OwnerGroupsPayload>(`/groups?${params.toString()}`);
  },
  audit: (limit = 50) => request<OwnerAuditPayload>(`/audit?limit=${limit}`),
  grantVip: (userId: number, payload: VipGrantPayload) =>
    request<VipMutationResult>(`/users/${userId}/vip`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  revokeVip: (userId: number, payload: VipRevokePayload) =>
    request<VipMutationResult>(`/users/${userId}/vip`, {
      method: "DELETE",
      body: JSON.stringify(payload),
    }),
  blockUser: (userId: number, reason: string) =>
    request(`/users/${userId}/block`, {
      method: "POST",
      body: JSON.stringify({ reason, confirmation: "ЗАБЛОКУВАТИ" }),
    }),
  unblockUser: (userId: number, reason: string) =>
    request(`/users/${userId}/unblock`, {
      method: "POST",
      body: JSON.stringify({ reason, confirmation: "РОЗБЛОКУВАТИ" }),
    }),
  saveNote: (userId: number, note: string) =>
    request(`/users/${userId}/note`, {
      method: "PATCH",
      body: JSON.stringify({ note, confirmation: "ЗБЕРЕГТИ НОТАТКУ" }),
    }),
  addTag: (userId: number, tag: string) =>
    request(`/users/${userId}/tags`, {
      method: "POST",
      body: JSON.stringify({ tag, confirmation: "ДОДАТИ ТЕГ" }),
    }),
  removeTag: (userId: number, tag: string) =>
    request(`/users/${userId}/tags/${encodeURIComponent(tag)}`, { method: "DELETE" }),
  adjustXp: (userId: number, amount: number, reason: string, telegramChatId?: number) =>
    request(`/users/${userId}/xp-adjustments`, {
      method: "POST",
      body: JSON.stringify({
        amount,
        reason,
        ...(telegramChatId ? { telegram_chat_id: telegramChatId } : {}),
        confirmation: "ЗМІНИТИ XP",
      }),
    }),
  setRole: (userId: number, role: StaffRole) =>
    request(`/users/${userId}/role`, {
      method: "PUT",
      body: JSON.stringify({ role, confirmation: "ЗМІНИТИ РОЛЬ" }),
    }),
  removeRole: (userId: number, reason: string) =>
    request(`/users/${userId}/role`, {
      method: "DELETE",
      body: JSON.stringify({ reason, confirmation: "ЗНЯТИ РОЛЬ" }),
    }),
  messageUser: (userId: number, messageText: string) =>
    request(`/users/${userId}/messages`, {
      method: "POST",
      body: JSON.stringify({ message_text: messageText, confirmation: "НАДІСЛАТИ" }),
    }),
  bulkUsers: (payload: Omit<BulkActionPayload, "confirmation">) =>
    request<BulkActionResult>("/users/bulk", {
      method: "POST",
      body: JSON.stringify({ ...payload, confirmation: "ВИКОНАТИ МАСОВУ ДІЮ" }),
    }),
  updateGroup: (
    chatId: number,
    payload: Partial<Pick<OwnerGroup, "is_active" | "is_paused" | "weekly_reports_enabled" | "report_card_theme">>,
  ) =>
    request<OwnerGroup>(`/groups/${chatId}`, {
      method: "PATCH",
      body: JSON.stringify({ ...payload, confirmation: "ЗБЕРЕГТИ" }),
    }),
};
