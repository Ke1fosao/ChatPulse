import type { ReportTheme } from "../api/types";

export type OwnerTab = "overview" | "users" | "groups" | "payments" | "audit";
export type VipFilter = "all" | "active" | "inactive" | "expiring";
export type UserStatusFilter = "all" | "active" | "inactive" | "blocked";
export type UserRoleFilter = "all" | "owner" | "admin" | "moderator" | "support" | "none";
export type UserPaymentFilter = "all" | "paid" | "never";
export type UserSort =
  | "activity_desc"
  | "activity_asc"
  | "created_desc"
  | "created_asc"
  | "xp_desc"
  | "xp_asc"
  | "groups_desc"
  | "groups_asc"
  | "stars_desc"
  | "stars_asc"
  | "vip_expiry_asc";
export type AdminRole = "owner" | "admin" | "moderator" | "support";
export type StaffRole = Exclude<AdminRole, "owner">;

export interface AccountAccess {
  plan: "free" | "vip" | "owner";
  is_owner: boolean;
  is_vip: boolean;
  vip_expires_at: string | null;
  entitlements: string[];
}

export interface OwnerActor {
  telegram_user_id: number;
  role: AdminRole;
  permissions: string[];
  is_owner: boolean;
}

export interface OwnerSession {
  owner: {
    telegram_id: number;
    display_name: string;
    username?: string | null;
    photo_url?: string | null;
  };
  actor: OwnerActor;
  account: AccountAccess;
}

export interface OwnerOverviewData {
  users_total: number;
  groups_total: number;
  active_groups: number;
  vip_total: number;
  messages_7d: number;
}

export interface OwnerUser {
  telegram_id: number;
  display_name: string;
  username?: string | null;
  global_xp_total: number;
  global_level: number;
  groups_count: number;
  is_vip: boolean;
  vip_expires_at: string | null;
  is_blocked: boolean;
  role: AdminRole | null;
  payment_count: number;
  stars_total: number;
  last_payment_at: string | null;
  created_at: string;
  last_activity_at: string;
}

export interface OwnerUsersPayload {
  items: OwnerUser[];
  total: number;
  limit: number;
  offset: number;
}

export interface OwnerUserFilters {
  query: string;
  vip: VipFilter;
  status: UserStatusFilter;
  role: UserRoleFilter;
  payment: UserPaymentFilter;
  tag: string;
  sort: UserSort;
  limit: number;
  offset: number;
}

export interface OwnerUserGroupDetail {
  telegram_chat_id: number;
  title: string;
  username?: string | null;
  xp_total: number;
  level: number;
  last_seen_at: string;
}

export interface OwnerUserAuditItem {
  id: number;
  actor_telegram_user_id: number;
  action: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface OwnerUserDetail {
  telegram_id: number;
  display_name: string;
  username?: string | null;
  language_code?: string | null;
  created_at: string;
  last_activity_at: string;
  global_xp_total: number;
  global_level: number;
  is_owner: boolean;
  role: AdminRole | null;
  is_blocked: boolean;
  restriction: {
    is_blocked: boolean;
    reason?: string | null;
    blocked_by_actor_id?: number | null;
    blocked_at?: string | null;
    unblocked_by_actor_id?: number | null;
    unblocked_at?: string | null;
    unblock_reason?: string | null;
    updated_at?: string;
  } | null;
  vip: {
    is_active: boolean;
    source: "payment" | "gifted" | null;
    starts_at: string | null;
    expires_at: string | null;
  };
  payment_summary: {
    stars_total: number;
    payment_count: number;
    last_payment_at: string | null;
    active_subscription: boolean;
  };
  note: string;
  tags: string[];
  groups: OwnerUserGroupDetail[];
  adjustments: Array<{
    id: number;
    telegram_chat_id: number | null;
    amount: number;
    previous_total: number;
    resulting_total: number;
    reason: string;
    actor_telegram_user_id: number;
    created_at: string;
  }>;
  deliveries: Array<{
    id: number;
    telegram_user_id: number;
    actor_telegram_user_id: number;
    message_text: string;
    status: "pending" | "sent" | "failed";
    safe_error?: string | null;
    created_at: string;
    sent_at?: string | null;
  }>;
  audit: OwnerUserAuditItem[];
}

export interface OwnerGroup {
  telegram_chat_id: number;
  title: string;
  username?: string | null;
  is_active: boolean;
  is_paused: boolean;
  weekly_reports_enabled: boolean;
  report_card_theme: ReportTheme;
  members_count: number;
  updated_at: string;
}

export interface OwnerGroupsPayload {
  items: OwnerGroup[];
  total: number;
}

export interface OwnerAuditEntry {
  id: number;
  owner_telegram_user_id: number;
  action: string;
  target_type: string;
  target_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface OwnerAuditPayload {
  items: OwnerAuditEntry[];
}

export interface VipGrantPayload {
  mode: "permanent" | "until";
  expires_at?: string;
  reason: string;
  confirmation: "ВИДАТИ VIP";
}

export interface VipRevokePayload {
  reason: string;
  confirmation: "ВІДКЛИКАТИ VIP";
}

export interface VipMutationResult {
  telegram_user_id: number;
  is_active: boolean;
  expires_at?: string | null;
}

export type BulkAction =
  | "grant_vip"
  | "revoke_vip"
  | "block"
  | "unblock"
  | "add_tag"
  | "remove_tag"
  | "message";

export interface BulkActionPayload {
  action: BulkAction;
  user_ids: number[];
  reason?: string;
  mode?: "permanent" | "until";
  expires_at?: string;
  tag?: string;
  message_text?: string;
  confirmation: "ВИКОНАТИ МАСОВУ ДІЮ";
}

export interface BulkActionResult {
  action: BulkAction;
  requested: number;
  succeeded: Array<{ user_id: number; result: unknown }>;
  failed: Array<{ user_id: number; error: string }>;
}

export interface RevenueSummary {
  period_days: number;
  stars: number;
  stars_today: number;
  stars_7d: number;
  stars_30d: number;
  stars_all_time: number;
  payments: number;
  unique_payers: number;
  average_payment: number;
  arppu_stars: number;
  active_paid_vip: number;
  active_gifted_vip: number;
  active_subscriptions: number;
  mrr_stars: number;
  refunds: number;
  refunded_stars: number;
  expiring_7d: number;
  trial_previews: number;
  trial_invoices: number;
  trial_paid: number;
  trial_converted: number;
  trial_conversion_percent: number;
}

export interface RevenueTimelinePoint {
  date: string;
  gross_stars: number;
  refunded_stars: number;
  net_stars: number;
  payments: number;
}

export interface RevenuePlanPoint {
  product_code: string;
  payments: number;
  stars: number;
}

export interface RevenueTransaction {
  id: number;
  telegram_user_id: number;
  display_name: string;
  username?: string | null;
  product_code: string;
  stars_amount: number;
  status: string;
  is_recurring: boolean;
  is_first_recurring: boolean;
  paid_at: string;
  granted_until?: string | null;
  subscription_expiration_date?: string | null;
  refunded_at?: string | null;
  refund_reason?: string | null;
  telegram_payment_charge_id: string;
}

export interface RevenueTransactionDetail extends RevenueTransaction {
  note: {
    id: number;
    text: string;
    updated_at: string;
  } | null;
  history: RevenueTransaction[];
  vip_grant: {
    is_active: boolean;
    expires_at: string | null;
    granted_by_owner_id: number | null;
    reason: string | null;
  };
  refund: {
    eligible: boolean;
    reason: string;
    stars?: number;
  };
}

export interface RevenueTransactionsPayload {
  items: RevenueTransaction[];
  total: number;
}
