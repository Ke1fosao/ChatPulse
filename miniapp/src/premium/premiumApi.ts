import { getInitData } from "../telegram/sdk";
import type { PremiumContextPayload, VipPlacementEvent } from "./types";

async function premiumRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  const initData = getInitData();
  if (initData) headers.set("X-Telegram-Init-Data", initData);
  if (init?.body) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/miniapp/v1/premium${path}`, { ...init, headers });
  if (!response.ok) {
    let message = "Не вдалося завантажити VIP-статус.";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Keep the stable user-facing fallback.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export const premiumApi = {
  context: () => premiumRequest<PremiumContextPayload>("/context"),
  event: (payload: VipPlacementEvent) =>
    premiumRequest<{ event: { id: number } }>("/events", {
      method: "POST",
      body: JSON.stringify({ ...payload, metadata: payload.metadata ?? {} }),
    }),
};
