import { Check, LockKeyhole, X } from "lucide-react";
import { useEffect } from "react";
import { createPortal } from "react-dom";
import { AchievementIcon } from "./AchievementVisual";
import type { AchievementChainCollectionItem } from "./achievementCollection";
import { chainLabels } from "./achievementCollection";

interface AchievementChainDialogProps {
  item: AchievementChainCollectionItem | null;
  onClose(): void;
}

export function AchievementChainDialog({ item, onClose }: AchievementChainDialogProps) {
  useEffect(() => {
    if (!item) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", keydown);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", keydown);
    };
  }, [item, onClose]);

  if (!item) return null;
  const title = chainLabels[item.chainKey] ?? item.chainKey.replaceAll("_", " ");

  return createPortal(
    <div className="achievement-chain-dialog" role="dialog" aria-modal="true" aria-label={title}>
      <button className="achievement-chain-dialog__backdrop" type="button" onClick={onClose} aria-label="Закрити" />
      <section className="achievement-chain-dialog__sheet">
        <header>
          <div>
            <p className="eyebrow">Шлях до легенди</p>
            <h2>{title}</h2>
            <span>{item.completedStages} з {item.totalStages} етапів виконано</span>
          </div>
          <button className="dialog-close" type="button" onClick={onClose} aria-label="Закрити деталі ланцюжка">
            <X size={20} />
          </button>
        </header>

        <div className="achievement-chain-path">
          {item.stages.map((achievement) => {
            const lockedSecret = achievement.hidden && !achievement.earned;
            return (
              <article
                className={`${achievement.earned ? "is-earned" : "is-locked"} achievement-chain-path__item--${achievement.rarity}`}
                key={achievement.code}
              >
                <span className="achievement-chain-path__marker">
                  {achievement.earned ? <Check size={17} /> : <LockKeyhole size={16} />}
                </span>
                <span className="achievement-chain-path__icon">
                  <AchievementIcon achievement={achievement} size={23} />
                </span>
                <div>
                  <small>ЕТАП {achievement.chain?.stage} З {achievement.chain?.total}</small>
                  <strong>{achievement.title}</strong>
                  <p>{lockedSecret ? "Умова засекречена" : achievement.description}</p>
                </div>
                <em>
                  {achievement.earned
                    ? "Отримано"
                    : `${achievement.progress.toLocaleString("uk-UA")} / ${achievement.threshold.toLocaleString("uk-UA")}`}
                </em>
              </article>
            );
          })}
        </div>

        <button className="primary-button" type="button" onClick={onClose}>Готово</button>
      </section>
    </div>,
    document.body,
  );
}
