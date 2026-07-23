import { CheckCircle2, ChevronRight } from "lucide-react";
import { AchievementIcon, rarityLabel } from "./AchievementVisual";
import type { AchievementChainCollectionItem } from "./achievementCollection";
import { chainLabels } from "./achievementCollection";

interface AchievementChainCardProps {
  item: AchievementChainCollectionItem;
  onOpen(item: AchievementChainCollectionItem): void;
}

export function AchievementChainCard({ item, onOpen }: AchievementChainCardProps) {
  const achievement = item.featuredAchievement;
  const label = chainLabels[item.chainKey] ?? item.chainKey.replaceAll("_", " ");
  const nearComplete = !item.earned && !item.hidden && item.progressPercent >= 70;
  return (
    <button
      className={`achievement-chain-card achievement-card--${achievement.rarity} ${
        item.earned ? "is-earned" : "is-progress"
      } ${nearComplete ? "is-near" : ""}`}
      type="button"
      onClick={() => onOpen(item)}
    >
      <span className="achievement-chain-card__icon">
        <AchievementIcon achievement={achievement} size={28} />
        {item.earned ? <i><CheckCircle2 size={14} /></i> : null}
      </span>
      <div className="achievement-chain-card__body">
        <div className="achievement-chain-card__heading">
          <div>
            <small>ЛАНЦЮЖОК · {item.completedStages}/{item.totalStages}</small>
            <strong>{label}</strong>
          </div>
          <span className="achievement-card__badges">
            {nearComplete ? (
              <em className="achievement-card__badge achievement-card__badge--near">МАЙЖЕ</em>
            ) : null}
            <em className="achievement-card__badge achievement-card__badge--rarity">
              {rarityLabel[achievement.rarity]}
            </em>
          </span>
        </div>
        <p>
          {item.nextAchievement ? (
            <>
              Наступна нагорода: <strong>{item.nextAchievement.title}</strong>
            </>
          ) : (
            "Усі етапи цього ланцюжка виконані"
          )}
        </p>
        <div
          className="achievement-chain-card__progress"
          aria-label={`Прогрес ${item.progressPercent}%`}
        >
          <span style={{ width: `${item.progressPercent}%` }} />
        </div>
        <div className="achievement-chain-card__meta">
          <span>
            {item.nextAchievement
              ? `${item.currentProgress.toLocaleString("uk-UA")} / ${item.nextAchievement.threshold.toLocaleString("uk-UA")}`
              : "Колекцію завершено"}
          </span>
          <strong>{item.progressPercent}%</strong>
        </div>
      </div>
      <ChevronRight size={19} />
    </button>
  );
}
