import { ArrowUpRight, Check, Circle, MessageCircleMore, Rocket, Users } from "lucide-react";
import type { OnboardingPayload } from "../../api/types";

interface OnboardingCardProps {
  onboarding: OnboardingPayload;
  onOpenTelegramLink(url: string): void;
}

const stepIcons = {
  start: Rocket,
  group: Users,
  activity: MessageCircleMore,
};

export function OnboardingCard({ onboarding, onOpenTelegramLink }: OnboardingCardProps) {
  if (onboarding.is_complete) return null;

  const nextStep = onboarding.steps.find((step) => !step.completed);
  const linkedGroupUrl = onboarding.linked_group?.username
    ? `https://t.me/${onboarding.linked_group.username}`
    : null;
  const actionUrl =
    onboarding.primary_action === "add_group"
      ? onboarding.add_group_url
      : onboarding.primary_action === "send_message"
        ? linkedGroupUrl
        : null;
  const actionLabel =
    onboarding.primary_action === "add_group" ? "Додати в групу" : "Відкрити групу";
  const progress = Math.round((onboarding.completed_steps / onboarding.total_steps) * 100);

  return (
    <section className="onboarding-card" aria-label="Швидкий старт ChatPulse">
      <header className="onboarding-card__header">
        <span className="onboarding-card__icon"><Rocket size={20} /></span>
        <div>
          <p className="eyebrow">Швидкий старт</p>
          <h2>Запусти перший пульс</h2>
        </div>
        <strong>{onboarding.completed_steps} із {onboarding.total_steps}</strong>
      </header>

      <div className="onboarding-card__progress" aria-label={`Виконано ${progress}%`}>
        <span style={{ width: `${progress}%` }} />
      </div>

      <div className="onboarding-card__steps">
        {onboarding.steps.map((step) => {
          const Icon = stepIcons[step.id];
          return (
            <article className={step.completed ? "is-complete" : ""} key={step.id}>
              <span className="onboarding-card__step-icon"><Icon size={17} /></span>
              <div>
                <strong>{step.title}</strong>
                <small>{step.description}</small>
              </div>
              {step.completed ? <Check size={18} /> : <Circle size={15} />}
            </article>
          );
        })}
      </div>

      <footer>
        <div>
          <small>Наступний крок</small>
          <strong>{nextStep?.title}</strong>
        </div>
        {actionUrl ? (
          <button type="button" onClick={() => onOpenTelegramLink(actionUrl)}>
            {actionLabel} <ArrowUpRight size={17} />
          </button>
        ) : (
          <span className="onboarding-card__hint">Напиши повідомлення у підключеній групі</span>
        )}
      </footer>
    </section>
  );
}
