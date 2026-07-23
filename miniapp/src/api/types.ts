export type Period = "week" | "month" | "all";
export type Metric = "xp" | "messages" | "reactions" | "replies" | "streak";
export type TabId = "home" | "groups" | "rankings" | "achievements" | "profile";
export type ReportTheme = "dark_pulse" | "telegram_wave" | "clean_light" | "aurora_gold";
export type AchievementRarity =
  | "common"
  | "uncommon"
  | "rare"
  | "epic"
  | "legendary"
  | "secret";

export interface AccountAccess {
  plan: "free" | "vip" | "owner";
  is_owner: boolean;
  is_vip: boolean;
  vip_expires_at: string | null;
  entitlements: string[];
}

export interface UserSummary {
  telegram_id: number;
  first_name: string;
  last_name?: string | null;
  display_name: string;
  username?: string | null;
  photo_url?: string | null;
}

export interface GlobalProgress {
  xp_total: number;
  level: number;
  tier: string;
  progress: number;
  needed: number;
  rank: number;
  total_users: number;
  percentile: number;
}

export interface QuickStats {
  xp_today: number;
  current_streak: number;
  longest_streak: number;
  protection_left: number;
  groups_count: number;
  messages_7d: number;
}

export interface ActivityPoint {
  date: string;
  xp: number;
  messages: number;
  reactions: number;
  replies?: number;
}

export interface Summary {
  messages_count: number;
  media_count: number;
  replies_count: number;
  reactions_received: number;
  photo_count: number;
  voice_count: number;
  night_messages_count: number;
  morning_messages_count: number;
  xp_earned: number;
  active_members: number;
}

export interface GroupCardData {
  telegram_chat_id: number;
  title: string;
  username?: string | null;
  initials: string;
  level: number;
  xp_total: number;
  current_streak: number;
  rank?: number | null;
  period: Summary;
  trend?: number | null;
  is_admin: boolean;
  last_activity_at: string;
}

export interface AchievementChain {
  key: string;
  stage: number;
  total: number;
}

export interface AchievementEarnedInstance {
  scope_key: string;
  telegram_chat_id: number | null;
  group_title: string | null;
  earned_at: string;
  progress: number;
}

export interface Achievement {
  code: string;
  title: string;
  description: string;
  category: string;
  rarity: AchievementRarity;
  scope: "group" | "global";
  icon: string;
  visual_theme: string;
  hidden: boolean;
  important: boolean;
  earned: boolean;
  earned_at?: string | null;
  group_title?: string | null;
  progress: number;
  threshold: number;
  comparator?: "gte" | "lte";
  chain?: AchievementChain | null;
  reward_xp: number;
  version: number;
  season_key?: string | null;
  earned_instances?: AchievementEarnedInstance[];
  primary_scope_key?: string | null;
}

interface AchievementEventBase {
  event_id: number;
  created_at: string;
}

export interface AchievementUnlockEventPayload extends AchievementEventBase {
  event_type: "unlock";
  achievement: Achievement;
}

export interface AchievementCollectionUpdateEventPayload extends AchievementEventBase {
  event_type: "collection_update";
  summary: {
    count: number;
    achievements: Achievement[];
  };
}

export type AchievementEventPayload =
  | AchievementUnlockEventPayload
  | AchievementCollectionUpdateEventPayload;

export interface RecentAchievement {
  code: string;
  title: string;
  description: string;
  rarity: AchievementRarity;
  earned_at: string;
  group_title: string;
}

export type OnboardingStepId = "start" | "group" | "activity";

export interface OnboardingStep {
  id: OnboardingStepId;
  title: string;
  description: string;
  completed: boolean;
}

export interface OnboardingPayload {
  completed_steps: number;
  total_steps: number;
  is_complete: boolean;
  primary_action: "add_group" | "send_message" | "done";
  add_group_url: string | null;
  linked_group?: {
    telegram_chat_id: number;
    title: string;
    username?: string | null;
  } | null;
  steps: OnboardingStep[];
}

export interface HomePayload {
  user: UserSummary;
  account: AccountAccess;
  onboarding: OnboardingPayload;
  global_progress: GlobalProgress;
  quick_stats: QuickStats;
  activity_series: ActivityPoint[];
  recent_achievements: RecentAchievement[];
  groups: GroupCardData[];
}

export interface RankingRow {
  rank: number;
  telegram_user_id: number;
  display_name: string;
  username?: string | null;
  value: number;
  metric: Metric;
  is_current_user: boolean;
  account_plan?: "free" | "vip" | "owner";
}

export interface RankingPayload {
  metric: Metric;
  period: Period;
  rows: RankingRow[];
  current_user?: RankingRow | null;
}

export interface HeatmapPoint {
  weekday: number;
  bucket: "night" | "morning" | "day";
  value: number;
}

export interface GroupSettings {
  is_paused: boolean;
  weekly_reports_enabled: boolean;
  timezone: "Europe/Kyiv" | "Europe/Warsaw" | "Europe/Berlin";
  report_weekday: number;
  report_time: string;
  report_card_theme: ReportTheme;
  track_messages: boolean;
  track_media: boolean;
  track_replies: boolean;
  track_reactions: boolean;
}

export interface GroupDashboard {
  group: {
    telegram_chat_id: number;
    title: string;
    username?: string | null;
    initials: string;
    timezone: string;
  };
  period: Period;
  overview: {
    current: Summary;
    previous: Summary;
    trends: Record<string, number | null>;
  };
  activity_series: ActivityPoint[];
  heatmap: HeatmapPoint[];
  personal_progress: {
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
  };
  leaderboard: RankingRow[];
  current_user_rank?: RankingRow | null;
  top_message?: {
    message_id: number;
    reactions_count: number;
    created_at: string;
    display_name: string;
    url?: string | null;
  } | null;
  popular_reaction?: { emoji: string; count: number } | null;
  nominations: Array<{
    metric: string;
    title: string;
    display_name: string;
    value: number;
  }>;
  settings: GroupSettings;
  capabilities?: { is_admin: boolean };
}

export interface ApiErrorBody {
  detail?: string;
}
