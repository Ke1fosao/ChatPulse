import { CheckCircle2, ChevronRight } from "lucide-react";
import type { Achievement } from "../api/types";
import { AchievementIcon, rarityLabel } from "../features/achievements/AchievementVisual";
import { achievementProgressPercent } from "../features/achievements/progress";

interface AchievementCardProps {
  achievement: Achievement;
  onOpen?(achievement: Achievement): void;
}

export function AchievementCard({ achievement, onOpen }: AchievementCardProps) {
  const lockedSecret = achievement.hidden && !achievement.earned;
  const progress = achievementProgressPercent(achievement);
  const nearComplete = !achievement.earned && !lockedSecret && progress >= 70;

  return (
    <button
      className={`achievement-card achievement-card--${achievement.rarity} ${
        achievement.earned ? "is-earned" : "is-locked"
      } ${nearComplete ? "is-near" : ""}`}
      type="button"
      onClick={() => onOpen?.(achievement)}
    >
      <span className="achievement-card__icon">
        <AchievementIcon achievement={achievement} size={24} />
        {achievement.earned ? <i><CheckCircle2 size={13} /></i> : null}
      </span>
      <div className="achievement-card__body">
        <div className="achievement-card__title">
          <strong>{achievement.title}</strong>
          <span className="achievement-card__badges">
            {nearComplete ? (
              <em className="achievement-card__badge achievement-card__badge--near">МАЙЖЕ</em>
            ) : null}
            <em className="achievement-card__badge achievement-card__badge--rarity">
              {rarityLabel[achievement.rarity]}
            </em>
          </span>
        </div>
        <p>{achievement.description}</p>

        {achievement.chain ? (
          <div className="achievement-card__chain">
            <span>{achievement.chain.key.replaceAll("_", " ")}</span>
            <strong>{achievement.chain.stage} / {achievement.chain.total}</strong>
          </div>
        ) : null}

        {!lockedSecret ? (
          <>
            <div className="achievement-progress" aria-label={`Прогрес ${progress}%`}>
              <span style={{ width: `${progress}%` }} />
            </div>
            <small>
              {achievement.earned
                ? `Отримано${achievement.group_title ? ` · ${achievement.group_title}` : ""}`
                : `${achievement.progress.toLocaleString("uk-UA")} / ${achievement.threshold.toLocaleString("uk-UA")}`}
            </small>
          </>
        ) : (
          <small className="achievement-card__secret-copy">Умова відкриється після виконання</small>
        )}
      </div>
      <ChevronRight className="achievement-card__chevron" size={16} />
    </button>
  );
}
