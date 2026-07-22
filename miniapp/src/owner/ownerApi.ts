import { getInitData } from "../telegram/sdk";
import type {
  OwnerAuditPayload,
  OwnerGroup,
  OwnerGroupsPayload,
  OwnerOverviewData,
  OwnerSession,
  OwnerUsersPayload,
  VipFilter,
  VipGrantPayload,
  VipMutationResult,
  VipRevokePayload,
} from "./types";

export class OwnerApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
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
    let detail = "Не вдалося виконати owner-запит.";
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // Keep the safe fallback message when the server did not return JSON.
    }
    throw new OwnerApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export const ownerApi = {
  session: () => request<OwnerSession>("/session"),
  overview: () => request<OwnerOverviewData>("/overview"),
  users: (query = "", vip: VipFilter = "all", limit = 50, offset = 0) => {
    const params = new URLSearchParams({ vip, limit: String(limit), offset: String(offset) });
    if (query.trim()) params.set("q", query.trim());
    return request<OwnerUsersPayload>(`/users?${params.toString()}`);
  },
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
  updateGroup: (
    chatId: number,
    payload: Partial<Pick<OwnerGroup, "is_active" | "is_paused" | "weekly_reports_enabled" | "report_card_theme">>,
  ) =>
    request<OwnerGroup>(`/groups/${chatId}`, {
      method: "PATCH",
      body: JSON.stringify({ ...payload, confirmation: "ЗБЕРЕГТИ" }),
    }),
};
