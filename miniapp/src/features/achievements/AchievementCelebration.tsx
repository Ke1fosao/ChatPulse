import { Check, Pin, Share2, Sparkles, Trophy } from "lucide-react";
import type { CSSProperties } from "react";
import { useEffect } from "react";
import { createPortal } from "react-dom";
import type { AchievementRarity } from "../../api/types";
import { haptic, notify } from "../../telegram/sdk";
import { AchievementIcon, rarityLabel } from "./AchievementVisual";
import { useAchievementCelebrations } from "./useAchievementCelebrations";

interface AchievementCelebrationLayerProps {
  onOpenCollection(): void;
}

type CelebrationMode = "toast" | "modal" | "fullscreen";

function celebrationMode(rarity: AchievementRarity): CelebrationMode {
  if (rarity === "common" || rarity === "uncommon") return "toast";
  if (rarity === "rare" || rarity === "epic") return "modal";
  return "fullscreen";
}

function celebrationHaptic(rarity: AchievementRarity): void {
  if (rarity === "legendary" || rarity === "secret") {
    haptic("heavy");
  } else if (rarity === "epic" || rarity === "rare") {
    haptic("medium");
  } else {
    haptic("light");
  }
  notify("success");
}

function Confetti({ rarity }: { rarity: AchievementRarity }) {
  const count = rarity === "legendary" || rarity === "secret" ? 56 : 28;
  return (
    <div className="achievement-confetti" aria-hidden="true">
      {Array.from({ length: count }, (_, index) => {
        const style = {
          "--particle-index": index,
          "--particle-x": `${(index * 37) % 100}%`,
          "--particle-delay": `${(index % 9) * 45}ms`,
          "--particle-rotate": `${(index * 47) % 360}deg`,
        } as CSSProperties;
        return <i key={index} style={style} />;
      })}
    </div>
  );
}

export function AchievementCelebrationLayer({
  onOpenCollection,
}: AchievementCelebrationLayerProps) {
  const celebrations = useAchievementCelebrations();
  const current = celebrations.current;
  const mode = current ? celebrationMode(current.achievement.rarity) : "fullscreen";

  useEffect(() => {
    if (current) celebrationHaptic(current.achievement.rarity);
  }, [current]);

  if (!celebrations.active) return null;

  const openCollection = async () => {
    if (celebrations.summaryMode) {
      await celebrations.dismissSummary();
    } else {
      await celebrations.dismissCurrent();
    }
    onOpenCollection();
  };

  const summaryTitle = celebrations.historicalSummary
    ? "Колекцію оновлено"
    : `Ще ${celebrations.summaryCount} нових досягнень`;
  const summaryDescription = celebrations.historicalSummary
    ? `Ми знайшли ${celebrations.summaryCount} досягнень, які ти вже виконав раніше. Найцінніші з них уже в колекції.`
    : "Ми додали їх до твоєї колекції, щоб не показувати забагато анімацій поспіль.";

  return createPortal(
    <div
      className={`achievement-celebration achievement-celebration--${
        celebrations.summaryMode ? "fullscreen" : mode
      } ${
        celebrations.summaryMode
          ? "achievement-celebration--summary"
          : `achievement-celebration--${current?.achievement.rarity ?? "common"}`
      }`}
      role="dialog"
      aria-modal={mode !== "toast"}
      aria-label={celebrations.summaryMode ? "Нові досягнення" : "Досягнення розблоковано"}
    >
      <div className="achievement-celebration__backdrop" />
      {!celebrations.summaryMode && current ? (
        <>
          {mode !== "toast" ? <Confetti rarity={current.achievement.rarity} /> : null}
          {mode === "fullscreen" ? (
            <div className="achievement-celebration__rays" aria-hidden="true" />
          ) : null}
          <section className="achievement-celebration__card">
            <p className="achievement-celebration__eyebrow">ДОСЯГНЕННЯ РОЗБЛОКОВАНО</p>
            <div className="achievement-celebration__icon-wrap">
              <span className="achievement-celebration__orbit" />
              <span className="achievement-celebration__icon">
                <AchievementIcon achievement={current.achievement} size={mode === "toast" ? 28 : 40} />
              </span>
            </div>
            <div className="achievement-celebration__copy">
              <div className="achievement-celebration__labels">
                <span className="achievement-celebration__rarity">
                  {rarityLabel[current.achievement.rarity]}
                </span>
                {current.achievement.reward_xp > 0 ? (
                  <strong className="achievement-celebration__reward">
                    +{current.achievement.reward_xp} XP
                  </strong>
                ) : null}
              </div>
              <h2>{current.achievement.title}</h2>
              <p>{current.achievement.description}</p>
              <div className="achievement-celebration__meta">
                <span>
                  {current.achievement.group_title ?? "Глобальний профіль ChatPulse"}
                </span>
                {current.achievement.chain ? (
                  <span>
                    Етап {current.achievement.chain.stage} з {current.achievement.chain.total}
                  </span>
                ) : null}
              </div>
            </div>
            <div className="achievement-celebration__actions">
              <button
                className="achievement-celebration__share"
                type="button"
                onClick={() => void celebrations.shareCurrent()}
                disabled={celebrations.busy}
              >
                <Share2 size={18} /> Поділитися
              </button>
              {current.achievement.primary_scope_key ? (
                <button
                  className="achievement-celebration__pin"
                  type="button"
                  onClick={() => void celebrations.pinCurrent()}
                  disabled={celebrations.busy || celebrations.pinned}
                >
                  {celebrations.pinned ? <Check size={18} /> : <Pin size={18} />}
                  {celebrations.pinned ? "Закріплено" : "Закріпити"}
                </button>
              ) : null}
              <button
                className="achievement-celebration__collection"
                type="button"
                onClick={() => void openCollection()}
                disabled={celebrations.busy}
              >
                <Trophy size={18} /> До колекції
              </button>
              <button
                className="achievement-celebration__continue"
                type="button"
                onClick={() => void celebrations.dismissCurrent()}
                disabled={celebrations.busy}
              >
                {celebrations.busy ? "Зберігаємо…" : "Продовжити"}
              </button>
            </div>
          </section>
        </>
      ) : (
        <section className="achievement-celebration__card achievement-celebration__summary-card">
          <span className="achievement-celebration__summary-icon"><Sparkles /></span>
          <p className="achievement-celebration__eyebrow">
            {celebrations.historicalSummary ? "ІСТОРІЮ ВРАХОВАНО" : "КОЛЕКЦІЯ ПОПОВНИЛАСЯ"}
          </p>
          <h2>{summaryTitle}</h2>
          <p>{summaryDescription}</p>
          <div className="achievement-celebration__summary-list">
            {celebrations.summaryItems.map((achievement) => (
              <article key={achievement.code}>
                <span><AchievementIcon achievement={achievement} size={22} /></span>
                <div>
                  <strong>{achievement.title}</strong>
                  <small>{rarityLabel[achievement.rarity]}</small>
                </div>
              </article>
            ))}
          </div>
          <div className="achievement-celebration__actions">
            <button
              className="achievement-celebration__collection"
              type="button"
              onClick={() => void openCollection()}
              disabled={celebrations.busy}
            >
              <Trophy size={18} /> Переглянути колекцію
            </button>
            <button
              className="achievement-celebration__continue"
              type="button"
              onClick={() => void celebrations.dismissSummary()}
              disabled={celebrations.busy}
            >
              {celebrations.busy ? "Зберігаємо…" : "Добре"}
            </button>
          </div>
        </section>
      )}
    </div>,
    document.body,
  );
}
