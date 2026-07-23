import type { Achievement } from "../api/types";
import { getInitData } from "../telegram/sdk";
import type {
  FeaturedAchievement,
  FeaturedAchievementSelection,
  VipPayment,
  VipPlansPayload,
  VipPlan,
} from "./types";

class VipApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

function headers(body = false, accept = "application/json"): Headers {
  const value = new Headers({ Accept: accept });
  const initData = getInitData();
  if (initData) value.set("X-Telegram-Init-Data", initData);
  if (body) value.set("Content-Type", "application/json");
  return value;
}

async function parseError(response: Response): Promise<VipApiError> {
  try {
    const body = (await response.json()) as { detail?: string };
    return new VipApiError(body.detail ?? "Не вдалося виконати дію.", response.status);
  } catch {
    return new VipApiError("Не вдалося виконати дію.", response.status);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/miniapp/v1${path}`, {
    ...init,
    headers: headers(Boolean(init?.body)),
  });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as T;
}

async function requestBlob(path: string, accept: string): Promise<Blob> {
  const response = await fetch(`/api/miniapp/v1${path}`, {
    headers: headers(false, accept),
  });
  if (!response.ok) throw await parseError(response);
  return response.blob();
}

export const vipApi = {
  plans: () => request<VipPlansPayload>("/vip/plans"),
  history: async () =>
    (await request<{ payments: VipPayment[] }>("/vip/history")).payments,
  invoice: (planCode: VipPlan["code"]) =>
    request<{ invoice_url: string }>("/vip/invoice", {
      method: "POST",
      body: JSON.stringify({ plan_code: planCode }),
    }),
  subscription: (canceled: boolean) =>
    request<{ ok: boolean; canceled: boolean }>("/vip/subscription", {
      method: "POST",
      body: JSON.stringify({ canceled }),
    }),
  exportGroup: (chatId: number, format: "csv" | "pdf", period = "month") =>
    requestBlob(
      `/vip/groups/${chatId}/export.${format}?period=${period}`,
      format === "csv" ? "text/csv" : "application/pdf",
    ),
  featured: async () =>
    (await request<{ items: FeaturedAchievement[] }>("/featured-achievements")).items,
  updateFeatured: async (items: FeaturedAchievementSelection[]) =>
    (
      await request<{ items: FeaturedAchievement[] }>("/featured-achievements", {
        method: "PUT",
        body: JSON.stringify({ items }),
      })
    ).items,
  achievements: async () =>
    (await request<{ achievements: Achievement[] }>("/achievements")).achievements,
};

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export { VipApiError };
