import {
  Check,
  ChevronRight,
  Crown,
  LockKeyhole,
  Sparkles,
  Trophy,
  X,
} from "lucide-react";
import { useEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import type { GlobalProgress, LevelCatalog } from "../../api/types";

interface LevelGuideDialogProps {
  open: boolean;
  progress: GlobalProgress;
  catalog: LevelCatalog;
  onClose(): void;
}

const milestoneLevels = [1, 5, 10, 20, 35, 50];

function formatXp(value: number): string {
  return `${value.toLocaleString("uk-UA")} XP`;
}

export function LevelGuideDialog({
  open,
  progress,
  catalog,
  onClose,
}: LevelGuideDialogProps) {
  const milestones = useMemo(
    () => catalog.levels.filter((level) => milestoneLevels.includes(level.level)),
    [catalog.levels],
  );

  useEffect(() => {
    if (!open) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.body.classList.add("profile-dialog-open");

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.body.classList.remove("profile-dialog-open");
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose, open]);

  if (!open) return null;

  const ratio = progress.needed <= 0
    ? 100
    : Math.min(100, Math.round((progress.progress / progress.needed) * 100));
  const remaining = Math.max(0, progress.needed - progress.progress);

  return createPortal(
    <div
      className="level-dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="level-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Усі рівні ChatPulse"
      >
        <header className="level-dialog__header">
          <div>
            <p className="eyebrow">Рівнева система</p>
            <h2>Усі {catalog.max_level} рівнів</h2>
            <span>XP з усіх груп формує твій глобальний статус</span>
          </div>
          <button type="button" className="dialog-close" onClick={onClose} aria-label="Закрити">
            <X size={20} />
          </button>
        </header>

        <section className="level-current-card">
          <div className="level-current-card__orb">
            <small>LEVEL</small>
            <strong>{progress.level}</strong>
          </div>
          <div className="level-current-card__copy">
            <span><Sparkles size={15} /> Поточний статус</span>
            <h3>{progress.tier}</h3>
            <strong>{progress.xp_total.toLocaleString("uk-UA")} XP</strong>
            <p>
              {progress.needed <= 0
                ? "Ти досяг максимального рівня ChatPulse."
                : `Ще ${remaining.toLocaleString("uk-UA")} XP до рівня ${progress.level + 1}.`}
            </p>
          </div>
          <div className="level-current-card__progress" aria-label={`Прогрес ${ratio}%`}>
            <span style={{ width: `${ratio}%` }} />
          </div>
        </section>

        <section className="tier-roadmap" aria-label="Ключові статуси">
          {milestones.map((milestone) => (
            <article
              key={milestone.level}
              className={`tier-roadmap__item ${milestone.unlocked ? "is-unlocked" : ""} ${milestone.is_current ? "is-current" : ""}`}
            >
              <span>
                {milestone.level === 50 ? (
                  <Crown size={18} />
                ) : milestone.unlocked ? (
                  <Check size={17} />
                ) : (
                  <LockKeyhole size={15} />
                )}
              </span>
              <strong>{milestone.milestone_label} · L{milestone.level}</strong>
              <small>{formatXp(milestone.xp_required)}</small>
            </article>
          ))}
        </section>

        {catalog.next_tier ? (
          <section className="next-tier-card">
            <span><Trophy size={20} /></span>
            <div>
              <p>Наступний великий статус</p>
              <strong>{catalog.next_tier.tier} на рівні {catalog.next_tier.level}</strong>
              <small>Потрібно {formatXp(catalog.next_tier.xp_required)}</small>
            </div>
            <ChevronRight size={18} />
          </section>
        ) : (
          <section className="next-tier-card next-tier-card--complete">
            <span><Crown size={20} /></span>
            <div>
              <p>Максимум досягнуто</p>
              <strong>Фінальний статус: Легенда</strong>
              <small>Тепер твоя ціль — утримувати активність і рейтинг</small>
            </div>
          </section>
        )}

        <div className="level-list-heading">
          <div>
            <p className="eyebrow">Повна шкала</p>
            <h3>Вимоги до кожного рівня</h3>
          </div>
          <span>{catalog.current_level}/{catalog.max_level}</span>
        </div>

        <section className="level-list" aria-label="Список рівнів">
          {catalog.levels.map((level) => (
            <article
              key={level.level}
              className={`level-row ${level.unlocked ? "is-unlocked" : ""} ${level.is_current ? "is-current" : ""} ${level.is_milestone ? "is-milestone" : ""}`}
            >
              <div className="level-row__number">
                {level.unlocked ? <Check size={14} /> : <span>{level.level}</span>}
              </div>
              <div className="level-row__copy">
                <div>
                  <strong>Рівень {level.level}</strong>
                  {level.milestone_label ? <em>{level.milestone_label}</em> : null}
                  {level.is_current ? <b>Ти тут</b> : null}
                </div>
                <p>{level.tier}</p>
              </div>
              <div className="level-row__requirement">
                <strong>{formatXp(level.xp_required)}</strong>
                <small>
                  {level.level === catalog.max_level
                    ? "максимум"
                    : `+${level.xp_to_next.toLocaleString("uk-UA")} XP`}
                </small>
              </div>
            </article>
          ))}
        </section>
      </section>
    </div>,
    document.body,
  );
}
