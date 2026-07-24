import { Award, Crown, Eye, Filter, LockKeyhole, Sparkles, Target } from "lucide-react";
import { useMemo, useState } from "react";
import type { Achievement, AchievementRarity } from "../../api/types";
import { AchievementCard } from "../../components/AchievementCard";
import { EmptyState } from "../../components/EmptyState";
import { usePremium } from "../../premium/PremiumContext";
import { AchievementChainCard } from "./AchievementChainCard";
import { AchievementChainDialog } from "./AchievementChainDialog";
import { AchievementDetailsDialog } from "./AchievementDetailsDialog";
import { FeaturedAchievements } from "./FeaturedAchievements";
import {
  buildAchievementCollection,
  collectionItemProgress,
  type AchievementChainCollectionItem,
} from "./achievementCollection";
import { achievementProgressPercent } from "./progress";

interface AchievementsPageProps {
  achievements: Achievement[];
  loading: boolean;
  onRefresh(): void;
}

const primaryTabs = [
  ["all", "Усі"],
  ["progress", "У процесі"],
  ["earned", "Отримані"],
  ["secret", "Секретні"],
] as const;

const categories = [
  ["all", "Усі категорії"],
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

const rarityFilters: Array<["all" | AchievementRarity, string]> = [
  ["all", "Будь-яка рідкість"],
  ["common", "Звичайні"],
  ["uncommon", "Незвичайні"],
  ["rare", "Рідкісні"],
  ["epic", "Епічні"],
  ["legendary", "Легендарні"],
  ["secret", "Секретні"],
];

export function AchievementsPage({
  achievements,
  loading,
  onRefresh,
}: AchievementsPageProps) {
  const [primaryTab, setPrimaryTab] =
    useState<(typeof primaryTabs)[number][0]>("all");
  const [category, setCategory] = useState<(typeof categories)[number][0]>("all");
  const [rarityFilter, setRarityFilter] = useState<"all" | AchievementRarity>("all");
  const [nearOnly, setNearOnly] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selected, setSelected] = useState<Achievement | null>(null);
  const [selectedChain, setSelectedChain] =
    useState<AchievementChainCollectionItem | null>(null);
  const premium = usePremium();

  const collection = useMemo(() => {
    const filteredAchievements = achievements
      .filter((item) => category === "all" || item.category === category)
      .filter((item) => rarityFilter === "all" || item.rarity === rarityFilter);

    return buildAchievementCollection(filteredAchievements)
      .filter((item) => {
        if (primaryTab === "earned") return item.earned;
        if (primaryTab === "progress") return !item.earned && !item.hidden;
        if (primaryTab === "secret") return item.hidden;
        return true;
      })
      .filter((item) => !nearOnly || (!item.earned && collectionItemProgress(item) >= 70))
      .sort((left, right) => {
        if (left.earned !== right.earned) return Number(right.earned) - Number(left.earned);
        return collectionItemProgress(right) - collectionItemProgress(left);
      });
  }, [achievements, category, nearOnly, primaryTab, rarityFilter]);

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
    <div className="page achievements-page achievement-collection-v3">
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
            <Crown size={18} />
            <div><strong>{legendary}</strong><span>легендарних</span></div>
          </article>
          <article>
            <Eye size={18} />
            <div><strong>{secret}</strong><span>секретних</span></div>
          </article>
          <article>
            <Target size={18} />
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
        <div className="achievement-primary-tabs" role="tablist" aria-label="Статус досягнень">
          {primaryTabs.map(([id, label]) => (
            <button
              className={primaryTab === id ? "is-active" : ""}
              key={id}
              type="button"
              role="tab"
              aria-selected={primaryTab === id}
              onClick={() => setPrimaryTab(id)}
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
            <Filter size={17} /> Фільтри
          </button>
          <span>{collection.length} результатів</span>
        </div>

        {filtersOpen ? (
          <div className="achievement-filter-panel panel">
            <label>
              <span>Категорія</span>
              <select
                value={category}
                onChange={(event) =>
                  setCategory(event.target.value as (typeof categories)[number][0])
                }
              >
                {categories.map(([id, label]) => (
                  <option key={id} value={id}>{label}</option>
                ))}
              </select>
            </label>
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
              className={`achievement-near-toggle ${nearOnly ? "is-active" : ""}`}
              type="button"
              onClick={() => setNearOnly((value) => !value)}
            >
              <Target size={17} /> Майже готові
            </button>
            <button
              className="achievement-filter-reset"
              type="button"
              onClick={() => {
                setPrimaryTab("all");
                setCategory("all");
                setRarityFilter("all");
                setNearOnly(false);
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
      ) : collection.length > 0 ? (
        <div className="achievement-list achievement-list--v3">
          {collection.map((item) =>
            item.kind === "chain" ? (
              <AchievementChainCard item={item} key={item.key} onOpen={setSelectedChain} />
            ) : (
              <AchievementCard
                achievement={item.achievement}
                key={item.key}
                onOpen={setSelected}
              />
            ),
          )}
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
        <Award size={20} />
        <div>
          <strong>Ланцюжки показують увесь шлях</strong>
          <p>Одна картка замінює десятки однакових порогів і одразу показує наступну нагороду.</p>
        </div>
        <span><LockKeyhole size={16} /> Секретні умови не розкриваються</span>
      </div>

      <AchievementDetailsDialog achievement={selected} onClose={() => setSelected(null)} />
      <AchievementChainDialog item={selectedChain} onClose={() => setSelectedChain(null)} />
    </div>
  );
}
