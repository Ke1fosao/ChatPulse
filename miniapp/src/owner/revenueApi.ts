import { getInitData } from "../telegram/sdk";
import type {
  RevenuePlanPoint,
  RevenueSummary,
  RevenueTimelinePoint,
  RevenueTransactionDetail,
  RevenueTransactionsPayload,
} from "./types";

export interface RevenueFilters {
  q?: string;
  product?: string;
  paymentStatus?: string;
  recurring?: "all" | "true" | "false";
  days?: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  const initData = getInitData();
  if (initData) headers.set("X-Telegram-Init-Data", initData);
  if (init?.body) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/owner/v1/payments${path}`, { ...init, headers });
  if (!response.ok) {
    let message = "Owner Revenue недоступний.";
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      // Use fallback.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

function filterQuery(filters: RevenueFilters, pagination = false): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.product) params.set("product", filters.product);
  if (filters.paymentStatus) params.set("payment_status", filters.paymentStatus);
  if (filters.recurring && filters.recurring !== "all") params.set("recurring", filters.recurring);
  if (filters.days) params.set("days", String(filters.days));
  if (pagination) {
    params.set("limit", "50");
    params.set("offset", "0");
  }
  return params;
}

export const revenueApi = {
  summary: (days: number) => request<RevenueSummary>(`/summary?days=${days}`),
  timeline: (days: number) =>
    request<{ items: RevenueTimelinePoint[] }>(`/timeline?days=${days}`).then((payload) => payload.items),
  plans: (days: number) =>
    request<{ items: RevenuePlanPoint[] }>(`/plans?days=${days}`).then((payload) => payload.items),
  transactions: (filters: RevenueFilters) =>
    request<RevenueTransactionsPayload>(`/transactions?${filterQuery(filters, true).toString()}`),
  detail: (paymentId: number) => request<RevenueTransactionDetail>(`/transactions/${paymentId}`),
  note: (paymentId: number, userId: number, text: string) =>
    request<{ note: { text: string } }>(`/transactions/${paymentId}/note`, {
      method: "PUT",
      body: JSON.stringify({ user_id: userId, text }),
    }),
  refund: (paymentId: number, reason: string, confirmation: string) =>
    request<{ ok: boolean }>(`/transactions/${paymentId}/refund`, {
      method: "POST",
      body: JSON.stringify({ reason, confirmation }),
    }),
  subscription: (userId: number, canceled: boolean, reason: string) =>
    request<{ ok: boolean; canceled: boolean }>("/subscription", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, canceled, reason }),
    }),
  exportCsv: async (filters: RevenueFilters) => {
    const headers = new Headers({ Accept: "text/csv" });
    const initData = getInitData();
    if (initData) headers.set("X-Telegram-Init-Data", initData);
    const response = await fetch(`/api/owner/v1/payments/export.csv?${filterQuery(filters).toString()}`, { headers });
    if (!response.ok) throw new Error("Не вдалося експортувати платежі.");
    return response.blob();
  },
};
