import type {
  Achievement,
  AchievementEventPayload,
  ApiErrorBody,
  GroupCardData,
  GroupDashboard,
  GroupSettings,
  HomePayload,
  Metric,
  OnboardingPayload,
  Period,
  RankingPayload,
} from "./types";
import type { LevelsPayload } from "./levels";
import { getInitData } from "../telegram/sdk";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

function requestHeaders(init?: RequestInit, accept = "application/json"): Headers {
  const headers = new Headers(init?.headers);
  headers.set("Accept", accept);
  const initData = getInitData();
  if (initData) headers.set("X-Telegram-Init-Data", initData);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return headers;
}

async function responseError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody = {};
  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    body = {};
  }
  return new ApiError(body.detail ?? "Не вдалося завантажити дані.", response.status);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/miniapp/v1${path}`, {
    ...init,
    headers: requestHeaders(init),
  });
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as T;
}

async function requestBlob(path: string): Promise<Blob> {
  const response = await fetch(`/api/miniapp/v1${path}`, {
    headers: requestHeaders(undefined, "image/png"),
  });
  if (!response.ok) throw await responseError(response);
  return response.blob();
}

export const api = {
  home: () => request<Omit<HomePayload, "onboarding">>("/home"),
  onboarding: () => request<OnboardingPayload>("/onboarding"),
  levels: () => request<LevelsPayload>("/levels"),
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
  achievementEvents: async (limit = 10) =>
    (await request<{ events: AchievementEventPayload[] }>(
      `/achievement-events?limit=${limit}`,
    )).events,
  achievementCard: (eventId: number) =>
    requestBlob(`/achievement-events/${eventId}/card`),
  markAchievementSeen: (eventId: number) =>
    request<{ ok: boolean }>(`/achievement-events/${eventId}/seen`, {
      method: "POST",
    }),
  markAchievementShared: (eventId: number) =>
    request<{ ok: boolean }>(`/achievement-events/${eventId}/shared`, {
      method: "POST",
    }),
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
  profileCard: () => requestBlob("/profile-card"),
  weeklyCard: (chatId: number) => requestBlob(`/groups/${chatId}/weekly-card`),
};

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
