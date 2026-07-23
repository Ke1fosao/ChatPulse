import type {
  Achievement,
  ActivityPoint,
  GroupCardData,
  GroupSettings,
  HeatmapPoint,
  Metric,
  Period,
  RankingRow,
  Summary,
} from "./types";

export type GroupStatusId = "needs_setup" | "active" | "quiet" | "inactive";
export type GroupStatusTone = "success" | "neutral" | "warning" | "muted";
export type GroupCenterTab = "overview" | "ranking" | "analytics" | "awards";

export interface GroupStatus {
  id: GroupStatusId;
  label: string;
  tone: GroupStatusTone;
  attention_reason?: string | null;
}

export interface GroupsV2CardData extends GroupCardData {
  status: GroupStatus;
  is_favorite: boolean;
  bot_operational: boolean;
  messages_today: number;
  messages_7d: number;
  attention_reason?: string | null;
}

export interface GroupCenterIdentity {
  telegram_chat_id: number;
  title: string;
  username?: string | null;
  initials: string;
  timezone?: string;
  status?: GroupStatus;
  telegram_url?: string | null;
}

export interface GroupPulsePayload {
  score: number;
  label: string;
  tone: string;
  components: {
    messages: number;
    members: number;
    engagement: number;
    continuity: number;
  };
  positive?: string | null;
  negative?: string | null;
}

export interface GroupInsight {
  id: string;
  kind: string;
  icon: string;
  title: string;
  description: string;
}

export interface GroupPersonalProgress {
  xp_total: number;
  level: number;
  tier: string;
  progress: number;
  needed: number;
  current_streak: number;
  longest_streak: number;
  protection_left: number;
  period: Summary;
  rank?: number | null;
  rank_change?: number | null;
}

export interface GroupOverviewPayload {
  group: GroupCenterIdentity;
  period: Period;
  pulse: GroupPulsePayload;
  personal_progress: GroupPersonalProgress;
  top_participants: RankingRow[];
  insights: GroupInsight[];
  top_message?: {
    message_id: number;
    reactions_count: number;
    created_at: string;
    display_name: string;
    url?: string | null;
  } | null;
  popular_reaction?: { emoji: string; count: number } | null;
  settings: GroupSettings;
  capabilities?: { is_admin: boolean };
}

export type GroupRankingRow = RankingRow & { rank_change?: number | null };

export interface GroupRankingPayload {
  metric: Metric;
  period: Period;
  rows: GroupRankingRow[];
  current_user?: GroupRankingRow | null;
}

export interface GroupAnalyticsPayload {
  group: GroupCenterIdentity;
  period: Period;
  overview: {
    current: Summary;
    previous: Summary;
    trends: Record<string, number | null>;
  };
  activity_series: ActivityPoint[];
  heatmap: HeatmapPoint[];
  popular_reaction?: { emoji: string; count: number } | null;
  settings: GroupSettings;
}

export interface GroupNomination {
  metric: string;
  title: string;
  display_name: string;
  value: number;
}

export interface GroupAwardsPayload {
  group: GroupCenterIdentity;
  period: Period;
  nominations: GroupNomination[];
  achievements: Achievement[];
  nearest: Achievement[];
  highlighted?: Achievement | null;
}

export interface GroupCenterCache {
  overview: GroupOverviewPayload | null;
  ranking: GroupRankingPayload | null;
  analytics: GroupAnalyticsPayload | null;
  awards: GroupAwardsPayload | null;
}

export function groupCacheKey(
  chatId: number,
  tab: GroupCenterTab,
  period: Period,
  metric?: Metric,
): string {
  return `${chatId}:${tab}:${period}:${metric ?? "default"}`;
}

export function isGroupsV2Card(group: GroupCardData): group is GroupsV2CardData {
  return "status" in group && "is_favorite" in group;
}
