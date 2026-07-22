import { Award, LockKeyhole, Sparkles } from "lucide-react";
import type { Achievement } from "../api/types";

interface AchievementCardProps {
  achievement: Achievement;
}

export function AchievementCard({ achievement }: AchievementCardProps) {
  const progress = Math.min(
    100,
    Math.round((achievement.progress / Math.max(achievement.threshold, 1)) * 100),
  );
  return (
    <article
      className={`achievement-card achievement-card--${achievement.rarity} ${
        achievement.earned ? "is-earned" : "is-locked"
      }`}
    >
      <span className="achievement-card__icon">
        {achievement.earned ? (
          achievement.important ? (
            <Sparkles size={22} />
          ) : (
            <Award size={22} />
          )
        ) : (
          <LockKeyhole size={20} />
        )}
      </span>
      <div className="achievement-card__body">
        <div className="achievement-card__title">
          <strong>{achievement.title}</strong>
          <em>{achievement.rarity === "epic" ? "ЕПІЧНЕ" : "ЗВИЧАЙНЕ"}</em>
        </div>
        <p>{achievement.description}</p>
        <div className="achievement-progress">
          <span style={{ width: `${progress}%` }} />
        </div>
        <small>
          {achievement.earned
            ? `Отримано${achievement.group_title ? ` · ${achievement.group_title}` : ""}`
            : `${achievement.progress} / ${achievement.threshold}`}
        </small>
      </div>
    </article>
  );
}
