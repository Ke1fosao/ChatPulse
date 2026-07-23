import type { AccountAccess, Achievement } from "../api/types";

export interface VipPlan {
  code: "trial_7d" | "monthly_30d" | "quarter_90d" | "year_365d";
  title: string;
  short_title: string;
  description: string;
  stars: number;
  duration_days: number;
  recurring: boolean;
  badge: string | null;
  subscription_period: number | null;
  available: boolean;
}

export interface VipBillingStatus {
  is_vip: boolean;
  vip_expires_at: string | null;
  trial_available: boolean;
  active_subscription: {
    product_code: string;
    expires_at: string;
    is_canceled: boolean;
  } | null;
}

export interface VipPlansPayload {
  account: AccountAccess;
  billing: VipBillingStatus;
  benefits: string[];
  plans: VipPlan[];
}

export interface VipPayment {
  id: number;
  product_code: string;
  stars_amount: number;
  status: string;
  is_recurring: boolean;
  is_first_recurring: boolean;
  paid_at: string;
  granted_until: string | null;
  refunded_at: string | null;
}

export interface FeaturedAchievementSelection {
  code: string;
  scope_key: string;
}

export interface FeaturedAchievement extends Achievement {
  slot: number;
  scope_key: string;
}
