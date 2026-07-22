import { Check, ChevronRight, Crown, LockKeyhole, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "../api/client";
import type { LevelsPayload } from "../api/levels";

interface LevelsDialogProps {
  open: boolean;
  onClose(): void;
}

export function LevelsDialog({ open, onClose }: LevelsDialogProps) {
  const [data, setData] = useState<LevelsPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const current = useMemo(
    () => data?.levels.find((level) => level.is_current) ?? null,
    [data],
  );

  useEffect(() => {
    if (!open) return undefined;
    document.body.classList.add("levels-dialog-open");
    if (!data) {
      setLoading(true);
      setError("");
      void api.levels()
        .then(setData)
        .catch((reason) => {
          setError(
            reason instanceof Error
              ? reason.message
              : "Не вдалося завантажити рівні.",
          );
        })
        .finally(() => setLoading(false));
    }
    return () => {
      document.body.classList.remove("levels-dialog-open");
    };
  }, [data, open]);

  useEffect(() => {
    if (!open || !current) return;
    window.setTimeout(() => {
      const element = document.querySelector<HTMLElement>(
        `[data-level="${current.level}"]`,
      );
      if (typeof element?.scrollIntoView === "function") {
        element.scrollIntoView({ block: "center" });
      }
    }, 80);
  }, [current, open]);

  if (!open) return null;

  return createPortal(
    <div className="levels-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="levels-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Усі рівні ChatPulse"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="levels-dialog__header">
          <div>
            <p className="eyebrow">Система прогресу</p>
            <h2>Шлях рівнів</h2>
            <span>Від першого повідомлення до діамантового статусу</span>
          </div>
          <button type="button" onClick={onClose} aria-label="Закрити рівні">
            <X size={20} />
          </button>
        </header>

        {loading ? (
          <div className="levels-loading">
            <Sparkles className="spin" /> Завантажуємо рівні…
          </div>
        ) : error ? (
          <div className="levels-loading levels-loading--error">{error}</div>
        ) : data ? (
          <>
            <section className="levels-current-card">
              <div className="levels-current-card__number">
                <small>LEVEL</small>
                <strong>{data.current_level}</strong>
              </div>
              <div>
                <p>Твій поточний статус</p>
                <h3>{current?.tier ?? "Новачок"}</h3>
                <span>{data.xp_total.toLocaleString("uk-UA")} XP загалом</span>
              </div>
              <Crown size={26} />
            </section>

            <div className="levels-summary">
              <span><strong>{data.max_level}</strong> рівнів</span>
              <span><strong>5</strong> статусів</span>
              <span><strong>{data.max_level - data.current_level}</strong> попереду</span>
            </div>

            <div className="levels-list">
              {data.levels.map((level) => (
                <article
                  key={level.level}
                  data-level={level.level}
                  className={`level-row ${level.is_current ? "is-current" : ""} ${level.is_unlocked ? "is-unlocked" : "is-locked"}`}
                >
                  <div className="level-row__marker">
                    {level.is_current ? (
                      <Sparkles size={18} />
                    ) : level.is_unlocked ? (
                      <Check size={17} />
                    ) : (
                      <LockKeyhole size={15} />
                    )}
                  </div>
                  <div className="level-row__main">
                    <div><strong>Рівень {level.level}</strong><span>{level.tier}</span></div>
                    <p>{level.xp_required.toLocaleString("uk-UA")} XP потрібно</p>
                    {level.rewards.length > 0 ? (
                      <div className="level-row__rewards">
                        {level.rewards.map((reward) => <em key={reward}>{reward}</em>)}
                      </div>
                    ) : null}
                  </div>
                  <div className="level-row__next">
                    {level.xp_to_next === null
                      ? "MAX"
                      : `+${level.xp_to_next.toLocaleString("uk-UA")}`}
                    <ChevronRight size={15} />
                  </div>
                </article>
              ))}
            </div>
          </>
        ) : null}
      </section>
    </div>,
    document.body,
  );
}
