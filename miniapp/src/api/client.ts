import type {
  Achievement,
  ApiErrorBody,
  GroupCardData,
  GroupDashboard,
  GroupSettings,
  HomePayload,
  Metric,
  Period,
  RankingPayload,
} from "./types";
import { getInitData } from "../telegram/sdk";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  const initData = getInitData();
  if (initData) headers.set("X-Telegram-Init-Data", initData);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`/api/miniapp/v1${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    let body: ApiErrorBody = {};
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = {};
    }
    throw new ApiError(body.detail ?? "Не вдалося завантажити дані.", response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  home: () => request<HomePayload>("/home"),
  groups: async () => (await request<{ groups: GroupCardData[] }>("/groups")).groups,
  group: (chatId: number, period: Period) =>
    request<GroupDashboard>(`/groups/${chatId}?period=${period}`),
  rankings: (chatId: number, metric: Metric, period: Period) =>
    request<RankingPayload>(
      `/groups/${chatId}/rankings?metric=${metric}&period=${period}`,
    ),
  achievements: async (chatId?: number) => {
    const query = chatId === undefined ? "" : `?chat_id=${chatId}`;
    return (await request<{ achievements: Achievement[] }>(`/achievements${query}`))
      .achievements;
  },
  updateSettings: (chatId: number, settings: Partial<GroupSettings>) =>
    request<GroupSettings>(`/groups/${chatId}/settings`, {
      method: "PATCH",
      body: JSON.stringify(settings),
    }),
  resetGroup: (chatId: number) =>
    request<{ ok: boolean }>(`/groups/${chatId}/reset`, {
      method: "POST",
      body: JSON.stringify({ confirmation: "СКИНУТИ" }),
    }),
};
