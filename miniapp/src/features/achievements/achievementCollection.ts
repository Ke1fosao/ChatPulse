import type { Achievement } from "../../api/types";
import { achievementProgressPercent } from "./progress";

export interface AchievementChainCollectionItem {
  kind: "chain";
  key: string;
  chainKey: string;
  stages: Achievement[];
  completedStages: number;
  totalStages: number;
  currentProgress: number;
  progressPercent: number;
  nextAchievement: Achievement | null;
  featuredAchievement: Achievement;
  earned: boolean;
  hidden: boolean;
}

export interface AchievementStandaloneCollectionItem {
  kind: "achievement";
  key: string;
  achievement: Achievement;
  earned: boolean;
  hidden: boolean;
  progressPercent: number;
}

export type AchievementCollectionItem =
  | AchievementChainCollectionItem
  | AchievementStandaloneCollectionItem;

export const chainLabels: Record<string, string> = {
  messages: "Повідомлення",
  replies: "Відповіді",
  reactions: "Реакції",
  photos: "Фотографії",
  voices: "Голосові",
  group_xp: "XP у групі",
  streak: "Серія активності",
  levels: "Рівні групи",
  media_total: "Усі медіа",
  global_xp: "Глобальний XP",
  groups: "Активні групи",
  active_days: "Активні дні",
  weekly_xp: "Тижневий XP",
  ranking: "Рейтинг",
};

export function collectionItemProgress(item: AchievementCollectionItem): number {
  return item.progressPercent;
}

export function buildAchievementCollection(
  achievements: Achievement[],
): AchievementCollectionItem[] {
  const chains = new Map<string, Achievement[]>();
  const standalone: AchievementStandaloneCollectionItem[] = [];

  for (const achievement of achievements) {
    const chainKey = achievement.chain?.key;
    if (!chainKey) {
      standalone.push({
        kind: "achievement",
        key: `achievement:${achievement.code}`,
        achievement,
        earned: achievement.earned,
        hidden: achievement.hidden,
        progressPercent: achievementProgressPercent(achievement),
      });
      continue;
    }
    const stages = chains.get(chainKey) ?? [];
    stages.push(achievement);
    chains.set(chainKey, stages);
  }

  const chainItems: AchievementChainCollectionItem[] = [...chains.entries()].map(
    ([chainKey, values]) => {
      const stages = [...values].sort(
        (left, right) => (left.chain?.stage ?? 0) - (right.chain?.stage ?? 0),
      );
      const completedStages = stages.filter((item) => item.earned).length;
      const nextAchievement = stages.find((item) => !item.earned) ?? null;
      const featuredAchievement = nextAchievement ?? stages.at(-1)!;
      return {
        kind: "chain" as const,
        key: `chain:${chainKey}`,
        chainKey,
        stages,
        completedStages,
        totalStages: stages.length,
        currentProgress: featuredAchievement.progress,
        progressPercent: achievementProgressPercent(featuredAchievement),
        nextAchievement,
        featuredAchievement,
        earned: completedStages === stages.length,
        hidden: stages.every((item) => item.hidden),
      };
    },
  );

  return [...chainItems, ...standalone].sort((left, right) => {
    if (left.earned !== right.earned) return Number(right.earned) - Number(left.earned);
    return collectionItemProgress(right) - collectionItemProgress(left);
  });
}
