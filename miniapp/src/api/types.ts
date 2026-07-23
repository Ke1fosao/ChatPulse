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
  is_admin?: boolean;
  settings?: GroupSettings;
}

export interface RankingRow {
  rank: number;
  telegram_user_id: number;
  display_name: string;
  username?: string | null;
  value: number;
  level: number;
  tier?: string;
  streak?: number;
}

export interface RankingPayload {
  chat_id: number;
  metric: Metric;
  period: Period;
  rows: RankingRow[];
  current_user?: RankingRow | null;
}

export interface Achievement {
  code: string;
  title: string;
  description: string;
  icon: string;
  category: string;
  rarity: AchievementRarity;
  earned: boolean;
  earned_at?: string | null;
  progress?: number;
  target?: number;
  is_secret?: boolean;
  near_complete?: boolean;
  tier?: string;
  featured?: boolean;
}

export interface AchievementEventPayload {
  id: number;
  achievement_code: string;
  title: string;
  description: string;
  icon: string;
  rarity: AchievementRarity;
  earned_at: string;
  telegram_chat_id?: number | null;
  group_title?: string | null;
  seen_at?: string | null;
  shared_at?: string | null;
}

export interface GroupSettings {
  timezone: string;
  weekly_reports_enabled: boolean;
  report_weekday: number;
  report_hour: number;
  report_minute: number;
  report_card_theme: ReportTheme;
  is_paused: boolean;
  track_messages: boolean;
  track_media: boolean;
  track_replies: boolean;
  track_reactions: boolean;
}

export interface OnboardingPayload {
  completed: boolean;
  dismissed: boolean;
  steps: Array<{
    id: string;
    title: string;
    description: string;
    completed: boolean;
  }>;
}

export interface HomePayload {
  user: UserSummary;
  account: AccountAccess;
  progress: GlobalProgress;
  quick_stats: QuickStats;
  activity: ActivityPoint[];
  top_groups: GroupCardData[];
  onboarding: OnboardingPayload;
}

export interface HeatmapPoint {
  date: string;
  count: number;
  intensity: number;
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

export interface ApiErrorDetail {
  code?: string;
  message?: string;
  reason?: string | null;
  [key: string]: unknown;
}

export interface ApiErrorBody {
  detail?: string | ApiErrorDetail;
}
