import type { AccountAccess, ActivityPoint, Summary } from "../api/types";

export type VipPlacementEventType =
  | "vip_viewed"
  | "vip_plan_selected"
  | "vip_invoice_opened"
  | "vip_payment_completed"
  | "vip_payment_canceled"
  | "vip_feature_previewed"
  | "vip_feature_unlocked";

export type PremiumAnalyticsPeriod = "quarter" | "half_year" | "year";

export interface PremiumAnalyticsRange {
  period: PremiumAnalyticsPeriod;
  days: number;
  start: string;
  end: string;
  overview: Summary;
  activity_series: ActivityPoint[];
}

export interface PremiumAnalyticsPayload extends PremiumAnalyticsRange {
  group: {
    telegram_chat_id: number;
    title: string;
    username?: string | null;
    initials: string;
    timezone: string;
  };
  comparison: PremiumAnalyticsRange | null;
  trends: Record<string, number | null>;
}

export interface PremiumContextPayload {
  account: AccountAccess;
  trial_available: boolean;
  active_subscription: {
    plan_code: string;
    expires_at: string;
    is_canceled: boolean;
    telegram_payment_charge_id: string;
  } | null;
}

export interface VipPlacementEvent {
  event_type: VipPlacementEventType;
  source: string;
  feature_key?: string | null;
  metadata?: Record<string, unknown>;
}
