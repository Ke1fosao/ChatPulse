export interface LevelDefinition {
  level: number;
  tier: string;
  xp_required: number;
  xp_to_next: number | null;
  is_unlocked: boolean;
  is_current: boolean;
  rewards: string[];
}

export interface LevelsPayload {
  current_level: number;
  xp_total: number;
  max_level: number;
  levels: LevelDefinition[];
}
