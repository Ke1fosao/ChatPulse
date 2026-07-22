import type { Achievement } from "../../api/types";

export function achievementProgressPercent(achievement: Achievement): number {
  if (achievement.hidden && !achievement.earned) return 0;
  if (achievement.earned) return 100;

  const progress = Math.max(achievement.progress, 0);
  const threshold = Math.max(achievement.threshold, 1);

  if (achievement.comparator === "lte") {
    if (progress <= 0) return 0;
    return Math.min(100, Math.round((threshold / progress) * 100));
  }

  return Math.min(100, Math.round((progress / threshold) * 100));
}
