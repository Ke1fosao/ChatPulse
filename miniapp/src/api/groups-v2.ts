import type { GroupCardData } from "./types";

export type GroupStatusId = "needs_setup" | "active" | "quiet" | "inactive";
export type GroupStatusTone = "success" | "neutral" | "warning" | "muted";

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

export function isGroupsV2Card(group: GroupCardData): group is GroupsV2CardData {
  return "status" in group && "is_favorite" in group;
}
