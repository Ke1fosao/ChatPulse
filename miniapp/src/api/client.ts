import type { LevelsPayload } from "./levels";
import type {
  GroupAnalyticsPayload,
  GroupAwardsPayload,
  GroupOverviewPayload,
  GroupRankingPayload,
  GroupsV2CardData,
} from "./groups-v2";
import type {
  Achievement,
  AchievementEventPayload,
  ApiErrorBody,
  GroupDashboard,
  GroupSettings,
  HomePayload,
  Metric,
  OnboardingPayload,
  Period,
  RankingPayload,
} from "./types";
import { getInitData } from "../telegram/sdk";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
    public readonly reason?: string | null,
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
  if (typeof body.detail === "string") {
    return new ApiError(body.detail, response.status);
  }
  if (body.detail && typeof body.detail === "object") {
    return new ApiError(
      typeof body.detail.message === "string"
        ? body.detail.message
        : "Не вдалося завантажити дані.",
      response.status,
      typeof body.detail.code === "string" ? body.detail.code : undefined,
      typeof body.detail.reason === "string" || body.detail.reason === null
        ? body.detail.reason
        : undefined,
    );
  }
  return new ApiError("Не вдалося завантажити дані.", response.status);
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
  home: async (): Promise<HomePayload> => {
    const [home, onboarding] = await Promise.all([
      request<Omit<HomePayload, "onboarding">>("/home"),
      request<OnboardingPayload>("/onboarding"),
    ]);
    return { ...home, onboarding };
  },
  onboarding: () => request<OnboardingPayload>("/onboarding"),
  levels: () => request<LevelsPayload>("/levels"),
  groups: async () =>
    (await request<{ groups: GroupsV2CardData[] }>("/groups-v2")).groups,
  setGroupFavorite: (chatId: number, isFavorite: boolean) =>
    request<{ telegram_chat_id: number; is_favorite: boolean }>(
      `/groups/${chatId}/favorite`,
      {
        method: "PUT",
        body: JSON.stringify({ is_favorite: isFavorite }),
      },
    ),
  groupOverview: (chatId: number, period: Period) =>
    request<GroupOverviewPayload>(`/groups/${chatId}/overview?period=${period}`),
  groupRanking: (chatId: number, metric: Metric, period: Period) =>
    request<GroupRankingPayload>(
      `/groups/${chatId}/ranking?metric=${metric}&period=${period}`,
    ),
  groupAnalytics: (chatId: number, period: Period) =>
    request<GroupAnalyticsPayload>(`/groups/${chatId}/analytics?period=${period}`),
  groupAwards: (chatId: number, period: Period) =>
    request<GroupAwardsPayload>(`/groups/${chatId}/awards?period=${period}`),
  sendGroupReport: (chatId: number) =>
    request<{ ok: boolean }>(`/groups/${chatId}/report-now`, { method: "POST" }),
  pauseGroupAnalytics: (chatId: number) =>
    request<{ telegram_chat_id: number; is_paused: boolean }>(
      `/groups/${chatId}/analytics/pause`,
      { method: "POST" },
    ),
  resumeGroupAnalytics: (chatId: number) =>
    request<{ telegram_chat_id: number; is_paused: boolean }>(
      `/groups/${chatId}/analytics/resume`,
      { method: "POST" },
    ),
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
  profileCard: () => requestBlob("/profile-card-showcase"),
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
