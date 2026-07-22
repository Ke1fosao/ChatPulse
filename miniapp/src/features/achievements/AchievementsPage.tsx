import { Award, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import type { Achievement } from "../../api/types";
import { AchievementCard } from "../../components/AchievementCard";
import { EmptyState } from "../../components/EmptyState";

interface AchievementsPageProps {
  achievements: Achievement[];
  loading: boolean;
  onRefresh(): void;
}

const categories = [
  ["all", "Усі"],
  ["activity", "Активність"],
  ["reactions", "Реакції"],
  ["media", "Медіа"],
  ["streak", "Серії"],
  ["levels", "Рівні"],
] as const;

export function AchievementsPage({
  achievements,
  loading,
  onRefresh,
}: AchievementsPageProps) {
  const [category, setCategory] = useState<(typeof categories)[number][0]>("all");
  const [earnedOnly, setEarnedOnly] = useState(false);

  const visible = useMemo(
    () =>
      achievements
        .filter((item) => category === "all" || item.category === category)
        .filter((item) => !earnedOnly || item.earned)
        .sort((left, right) => Number(right.earned) - Number(left.earned)),
    [achievements, category, earnedOnly],
  );
  const unlocked = achievements.filter((item) => item.earned).length;
  const completion = achievements.length
    ? Math.round((unlocked / achievements.length) * 100)
    : 0;

  return (
    <div className="page achievements-page">
      <header className="achievement-hero panel">
        <span className="achievement-hero__icon"><Sparkles /></span>
        <div>
          <p className="eyebrow">Твоя колекція</p>
          <h2>{unlocked} з {achievements.length}</h2>
          <span>досягнень розблоковано</span>
        </div>
        <strong>{completion}%</strong>
        <div className="achievement-hero__progress">
          <span style={{ width: `${completion}%` }} />
        </div>
      </header>

      <div className="metric-tabs metric-tabs--scroll">
        {categories.map(([id, label]) => (
          <button
            className={category === id ? "is-active" : ""}
            key={id}
            type="button"
            onClick={() => setCategory(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <button
        className={`filter-chip filter-chip--wide ${earnedOnly ? "is-active" : ""}`}
        type="button"
        onClick={() => setEarnedOnly((value) => !value)}
      >
        <Award size={16} /> Показати лише отримані
      </button>

      {loading ? (
        <div className="skeleton-list">
          {Array.from({ length: 4 }, (_, index) => <span key={index} />)}
        </div>
      ) : visible.length > 0 ? (
        <div className="achievement-list">
          {visible.map((achievement) => (
            <AchievementCard achievement={achievement} key={achievement.code} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="У цій категорії поки порожньо"
          description="Продовжуй бути активним у групах — прогрес уже рахується."
          actionLabel="Оновити"
          onAction={onRefresh}
        />
      )}
    </div>
  );
}
