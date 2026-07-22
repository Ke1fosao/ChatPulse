import type { ReportTheme } from "../api/types";

export type OwnerTab = "overview" | "users" | "groups" | "audit";
export type VipFilter = "all" | "active" | "inactive";

export interface AccountAccess {
  plan: "free" | "vip" | "owner";
  is_owner: boolean;
  is_vip: boolean;
  vip_expires_at: string | null;
  entitlements: string[];
}

export interface OwnerSession {
  owner: {
    telegram_id: number;
    display_name: string;
    username?: string | null;
    photo_url?: string | null;
  };
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
  groups_count: number;
  is_vip: boolean;
  vip_expires_at: string | null;
  last_activity_at: string;
}

export interface OwnerUsersPayload {
  items: OwnerUser[];
  total: number;
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
