import { CalendarDays, CheckCircle2, LockKeyhole, X, Zap } from "lucide-react";
import { useEffect } from "react";
import { createPortal } from "react-dom";
import type { Achievement } from "../../api/types";
import { haptic } from "../../telegram/sdk";
import { AchievementIcon, rarityLabel } from "./AchievementVisual";
import { achievementProgressPercent } from "./progress";

interface AchievementDetailsDialogProps {
  achievement: Achievement | null;
  onClose(): void;
}

function formatEarnedAt(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("uk-UA", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function AchievementDetailsDialog({
  achievement,
  onClose,
}: AchievementDetailsDialogProps) {
  useEffect(() => {
    if (!achievement) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [achievement, onClose]);

  if (!achievement) return null;

  const lockedSecret = achievement.hidden && !achievement.earned;
  const progress = achievementProgressPercent(achievement);
  const earnedAt = formatEarnedAt(achievement.earned_at);

  return createPortal(
    <div className="achievement-details" role="dialog" aria-modal="true">
      <button
        className="achievement-details__backdrop"
        aria-label="Закрити"
        type="button"
        onClick={onClose}
      />
      <section className={`achievement-details__sheet achievement-details__sheet--${achievement.rarity}`}>
        <header>
          <span className="achievement-details__rarity">{rarityLabel[achievement.rarity]}</span>
          <button
            className="dialog-close"
            type="button"
            aria-label="Закрити деталі"
            onClick={onClose}
          >
            <X size={19} />
          </button>
        </header>

        <div className="achievement-details__icon">
          <AchievementIcon achievement={achievement} size={42} />
        </div>
        <h2>{achievement.title}</h2>
        <p>{achievement.description}</p>

        {lockedSecret ? (
          <div className="achievement-details__secret">
            <LockKeyhole size={20} />
            <div>
              <strong>Умова засекречена</strong>
              <span>Продовжуй користуватися ChatPulse — момент розблокування буде несподіваним.</span>
            </div>
          </div>
        ) : (
          <div className="achievement-details__progress-block">
            <div>
              <span>{achievement.earned ? "Виконано" : "Поточний прогрес"}</span>
              <strong>{progress}%</strong>
            </div>
            <div className="achievement-details__progress">
              <span style={{ width: `${progress}%` }} />
            </div>
            <small>
              {achievement.progress.toLocaleString("uk-UA")} із {achievement.threshold.toLocaleString("uk-UA")}
            </small>
          </div>
        )}

        <div className="achievement-details__facts">
          {achievement.chain ? (
            <article>
              <span><Zap size={17} /></span>
              <div>
                <small>Ланцюжок</small>
                <strong>Етап {achievement.chain.stage} з {achievement.chain.total}</strong>
              </div>
            </article>
          ) : null}
          <article>
            <span>{achievement.earned ? <CheckCircle2 size={17} /> : <LockKeyhole size={17} />}</span>
            <div>
              <small>Статус</small>
              <strong>{achievement.earned ? "Отримано" : "Ще не виконано"}</strong>
            </div>
          </article>
          {earnedAt ? (
            <article>
              <span><CalendarDays size={17} /></span>
              <div>
                <small>Дата отримання</small>
                <strong>{earnedAt}</strong>
              </div>
            </article>
          ) : null}
        </div>

        {achievement.group_title ? (
          <p className="achievement-details__group">Група: {achievement.group_title}</p>
        ) : null}

        <button
          className="primary-button achievement-details__close-button"
          type="button"
          onClick={() => {
            haptic("light");
            onClose();
          }}
        >
          Зрозуміло
        </button>
      </section>
    </div>,
    document.body,
  );
}
