import {
  Award,
  CalendarCheck2,
  Crown,
  Flame,
  Globe2,
  Heart,
  Image,
  ListOrdered,
  LockKeyhole,
  Medal,
  MessageCircle,
  Mic,
  MoonStar,
  Orbit,
  Reply,
  Sparkles,
  SunMedium,
  Trophy,
  UsersRound,
  Zap,
} from "lucide-react";
import type { ComponentType } from "react";
import type { Achievement, AchievementRarity } from "../../api/types";

export const rarityLabel: Record<AchievementRarity, string> = {
  common: "ЗВИЧАЙНЕ",
  uncommon: "НЕЗВИЧАЙНЕ",
  rare: "РІДКІСНЕ",
  epic: "ЕПІЧНЕ",
  legendary: "ЛЕГЕНДАРНЕ",
  secret: "СЕКРЕТНЕ",
};

const iconByName: Record<string, ComponentType<{ size?: number; strokeWidth?: number }>> = {
  "message-circle": MessageCircle,
  reply: Reply,
  heart: Heart,
  image: Image,
  mic: Mic,
  "audio-lines": Mic,
  zap: Zap,
  flame: Flame,
  trophy: Trophy,
  crown: Crown,
  medal: Medal,
  sparkles: Sparkles,
  "moon-star": MoonStar,
  sunrise: SunMedium,
  orbit: Orbit,
  "globe-2": Globe2,
  "users-round": UsersRound,
  "calendar-check-2": CalendarCheck2,
  "calendar-days": CalendarCheck2,
  "list-ordered": ListOrdered,
  "gallery-horizontal": Image,
  "scan-search": Sparkles,
  "cloud-lightning": Zap,
};

export function AchievementIcon({
  achievement,
  size = 24,
}: {
  achievement: Achievement;
  size?: number;
}) {
  if (achievement.hidden && !achievement.earned) {
    return <LockKeyhole size={size} strokeWidth={1.9} />;
  }
  if (achievement.rarity === "legendary") {
    return <Crown size={size} strokeWidth={1.9} />;
  }
  if (achievement.rarity === "secret") {
    return <Sparkles size={size} strokeWidth={1.9} />;
  }
  const Icon = iconByName[achievement.icon] ?? Award;
  return <Icon size={size} strokeWidth={1.9} />;
}
