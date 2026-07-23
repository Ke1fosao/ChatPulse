import {
  Award,
  Crown,
  Eye,
  Filter,
  LockKeyhole,
  Sparkles,
  Target,
} from "lucide-react";
import { useMemo, useState } from "react";
import type { Achievement, AchievementRarity } from "../../api/types";
import { AchievementCard } from "../../components/AchievementCard";
import { EmptyState } from "../../components/EmptyState";
import { usePremium } from "../../premium/PremiumContext";
import { AchievementDetailsDialog } from "./AchievementDetailsDialog";
import { FeaturedAchievements } from "./FeaturedAchievements";
import { achievementProgressPercent } from "./progress";

interface AchievementsPageProps {
  achievements: Achievement[];
  loading: boolean;
  onRefresh(): void;
}

const categories = [
  ["all", "Усі"],
  ["activity", "Активність"],
  ["dialogue", "Діалоги"],
  ["reactions", "Реакції"],
  ["media", "Медіа"],
  ["streak", "Серії"],
  ["levels", "Рівні"],
  ["ranking", "Рейтинг"],
  ["global", "Глобальні"],
  ["secret", "Секретні"],
] as const;

const statusFilters = [
  ["all", "Усі"],
  ["earned", "Отримані"],
  ["near", "Майже готові"],
  ["locked", "Не виконані"],
  ["secret", "Секретні"],
] as const;

const rarityFilters: Array<["all" | AchievementRarity, string]> = [
  ["all", "Будь-яка рідкість"],
  ["common", "Звичайні"],
  ["uncommon", "Незвичайні"],
  ["rare", "Рідкісні"],
  ["epic", "Епічні"],
  ["legendary", "Легендарні"],
  ["secret", "Секретні"],
];

const rarityWeight: Record<AchievementRarity, number> = {
  common: 1,
  uncommon: 2,
  rare: 3,
  epic: 4,
  legendary: 5,
  secret: 6,
};

export function AchievementsPage({
  achievements,
  loading,
  onRefresh,
}: AchievementsPageProps) {
  const [category, setCategory] = useState<(typeof categories)[number][0]>("all");
  const [statusFilter, setStatusFilter] =
    useState<(typeof statusFilters)[number][0]>("all");
  const [rarityFilter, setRarityFilter] = useState<"all" | AchievementRarity>("all");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selected, setSelected] = useState<Achievement | null>(null);
  const premium = usePremium();

  const visible = useMemo(
    () =>
      achievements
        .filter((item) => category === "all" || item.category === category)
        .filter((item) => rarityFilter === "all" || item.rarity === rarityFilter)
        .filter((item) => {
          if (statusFilter === "earned") return item.earned;
          if (statusFilter === "locked") return !item.earned;
          if (statusFilter === "secret") return item.hidden;
          if (statusFilter === "near") {
            return (
              !item.earned &&
              !item.hidden &&
              achievementProgressPercent(item) >= 70
            );
          }
          return true;
        })
        .sort((left, right) => {
          if (left.earned !== right.earned) {
            return Number(right.earned) - Number(left.earned);
          }
          const progressDifference =
            achievementProgressPercent(right) - achievementProgressPercent(left);
          if (progressDifference !== 0) return progressDifference;
          return rarityWeight[right.rarity] - rarityWeight[left.rarity];
        }),
    [achievements, category, rarityFilter, statusFilter],
  );

  const unlocked = achievements.filter((item) => item.earned).length;
  const completion = achievements.length
    ? Math.round((unlocked / achievements.length) * 100)
    : 0;
  const legendary = achievements.filter(
    (item) => item.earned && item.rarity === "legendary",
  ).length;
  const secret = achievements.filter((item) => item.earned && item.hidden).length;
  const near = achievements.filter(
    (item) =>
      !item.earned &&
      !item.hidden &&
      achievementProgressPercent(item) >= 70,
  ).length;

  return (
    <div className="page achievements-page achievement-collection-v2">
      <header className="achievement-hero achievement-hero--v2 panel">
        <span className="achievement-hero__icon"><Sparkles /></span>
        <div className="achievement-hero__copy">
          <p className="eyebrow">Твоя колекція</p>
          <h2>{unlocked} з {achievements.length}</h2>
          <span>досягнень розблоковано</span>
        </div>
        <strong>{completion}%</strong>
        <div className="achievement-hero__progress">
          <span style={{ width: `${completion}%` }} />
        </div>
        <div className="achievement-hero__stats">
          <article>
            <Crown size={16} />
            <div><strong>{legendary}</strong><span>легендарних</span></div>
          </article>
          <article>
            <Eye size={16} />
            <div><strong>{secret}</strong><span>секретних</span></div>
          </article>
          <article>
            <Target size={16} />
            <div><strong>{near}</strong><span>майже готові</span></div>
          </article>
        </div>
      </header>

      <FeaturedAchievements
        account={premium.account}
        achievements={achievements}
        trialAvailable={premium.trialAvailable}
        onOpenVip={premium.openVip}
      />

      <section className="achievement-collection__controls">
        <div className="metric-tabs metric-tabs--scroll achievement-category-tabs">
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

        <div className="achievement-filter-toolbar">
          <button
            className={`filter-chip filter-chip--wide ${filtersOpen ? "is-active" : ""}`}
            type="button"
            onClick={() => setFiltersOpen((value) => !value)}
          >
            <Filter size={15} /> Фільтри
          </button>
          <span>{visible.length} результатів</span>
        </div>

        {filtersOpen ? (
          <div className="achievement-filter-panel panel">
            <div>
              <span>Статус</span>
              <div className="achievement-filter-options">
                {statusFilters.map(([id, label]) => (
                  <button
                    className={statusFilter === id ? "is-active" : ""}
                    key={id}
                    type="button"
                    onClick={() => setStatusFilter(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <label>
              <span>Рідкість</span>
              <select
                value={rarityFilter}
                onChange={(event) =>
                  setRarityFilter(event.target.value as "all" | AchievementRarity)
                }
              >
                {rarityFilters.map(([id, label]) => (
                  <option key={id} value={id}>{label}</option>
                ))}
              </select>
            </label>
            <button
              className="achievement-filter-reset"
              type="button"
              onClick={() => {
                setCategory("all");
                setStatusFilter("all");
                setRarityFilter("all");
              }}
            >
              Скинути всі фільтри
            </button>
          </div>
        ) : null}
      </section>

      {loading ? (
        <div className="skeleton-list">
          {Array.from({ length: 5 }, (_, index) => <span key={index} />)}
        </div>
      ) : visible.length > 0 ? (
        <div className="achievement-list achievement-list--v2">
          {visible.map((achievement) => (
            <AchievementCard
              achievement={achievement}
              key={achievement.code}
              onOpen={setSelected}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="За цими фільтрами нічого немає"
          description="Зміни фільтри або продовжуй бути активним — прогрес уже рахується."
          actionLabel="Оновити"
          onAction={onRefresh}
        />
      )}

      <div className="achievement-collection__legend panel">
        <Award size={18} />
        <div>
          <strong>Рідкість справді має значення</strong>
          <p>Кожен тип має власний стиль картки та окреме повноекранне святкування.</p>
        </div>
        <span><LockKeyhole size={15} /> Секретні умови не розкриваються</span>
      </div>

      <AchievementDetailsDialog achievement={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
