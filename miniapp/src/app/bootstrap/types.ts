import type { GroupsV2CardData } from "../../api/groups-v2";
import type { Achievement, HomePayload, OnboardingPayload } from "../../api/types";

export type ResourceStatus = "idle" | "loading" | "success" | "error";

export interface ResourceState<T> {
  status: ResourceStatus;
  data: T | null;
  error: string;
}

export interface BootstrapResources {
  home: ResourceState<HomePayload>;
  groups: ResourceState<GroupsV2CardData[]>;
  achievements: ResourceState<Achievement[]>;
  onboarding: ResourceState<OnboardingPayload>;
  blockedAccount: { reason: string | null } | null;
  reloadCritical(): Promise<void>;
  retryGroups(): Promise<void>;
  retryAchievements(): Promise<void>;
  retryOnboarding(): Promise<void>;
  setGroups(updater: (current: GroupsV2CardData[]) => GroupsV2CardData[]): void;
  setAchievements(items: Achievement[]): void;
}
