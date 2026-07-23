import { Activity, Search, SlidersHorizontal, Sparkles, Star } from "lucide-react";
import { useMemo, useState } from "react";
import type { GroupsV2CardData, GroupStatusId } from "../../api/groups-v2";
import type { GroupCardData } from "../../api/types";
import { EmptyState } from "../../components/EmptyState";
import { GroupCard } from "../../components/GroupCard";

interface GroupsPageProps {
  groups: GroupsV2CardData[];
  onOpenGroup(group: GroupCardData): void;
  onToggleFavorite(group: GroupsV2CardData, nextValue: boolean): Promise<void> | void;
  onRefresh(): void;
}

type SortMode = "smart" | "activity" | "recent" | "trend" | "xp";
type FilterMode = "all" | "active" | "quiet" | "admin" | "setup" | "favorite";

const filters: Array<{ id: FilterMode; label: string }> = [
  { id: "all", label: "Усі" },
  { id: "active", label: "Активні" },
  { id: "quiet", label: "Тихі" },
  { id: "admin", label: "Я адмін" },
  { id: "setup", label: "Потрібне налаштування" },
  { id: "favorite", label: "Обране" },
];

function smartWeight(group: GroupsV2CardData): number {
  if (group.status.id === "needs_setup") return 0;
  if (group.is_favorite) return 1;
  if (group.status.id === "active") return 2;
  if (group.status.id === "quiet") return 3;
  return 4;
}

function matchesFilter(group: GroupsV2CardData, filter: FilterMode): boolean {
  if (filter === "all") return true;
  if (filter === "admin") return group.is_admin;
  if (filter === "setup") return group.status.id === "needs_setup";
  if (filter === "favorite") return group.is_favorite;
  return group.status.id === filter;
}

function timestamp(value: string): number {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function statusCount(groups: GroupsV2CardData[], status: GroupStatusId): number {
  return groups.filter((group) => group.status.id === status).length;
}

export function GroupsPage({
  groups,
  onOpenGroup,
  onToggleFavorite,
  onRefresh,
}: GroupsPageProps) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortMode>("smart");
  const [filter, setFilter] = useState<FilterMode>("all");
  const [favoriteBusy, setFavoriteBusy] = useState<number | null>(null);

  const visibleGroups = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("uk-UA");
    return groups
      .filter((group) => matchesFilter(group, filter))
      .filter((group) => group.title.toLocaleLowerCase("uk-UA").includes(normalized))
      .sort((left, right) => {
        if (sort === "smart") {
          const priority = smartWeight(left) - smartWeight(right);
          if (priority !== 0) return priority;
          return timestamp(right.last_activity_at) - timestamp(left.last_activity_at);
        }
        if (sort === "activity") return right.messages_7d - left.messages_7d;
        if (sort === "trend") return (right.trend ?? -999) - (left.trend ?? -999);
        if (sort === "xp") return right.xp_total - left.xp_total;
        return timestamp(right.last_activity_at) - timestamp(left.last_activity_at);
      });
  }, [filter, groups, query, sort]);

  const activeCount = statusCount(groups, "active");
  const setupCount = statusCount(groups, "needs_setup");
  const adminCount = groups.filter((group) => group.is_admin).length;

  const toggleFavorite = async (group: GroupsV2CardData, nextValue: boolean) => {
    setFavoriteBusy(group.telegram_chat_id);
    try {
      await onToggleFavorite(group, nextValue);
    } finally {
      setFavoriteBusy(null);
    }
  };

  return (
    <div className="page groups-v2-page">
      <header className="groups-v2-hero">
        <div>
          <p className="eyebrow">Твої Telegram-простори</p>
          <h2>Групи</h2>
          <p>Одразу видно, де кипить розмова, а де потрібна твоя увага.</p>
        </div>
        <span className="groups-v2-hero__mark">
          <Sparkles size={22} />
        </span>
      </header>

      <section className="groups-summary" aria-label="Короткий огляд груп">
        <article>
          <strong>{groups.length}</strong>
          <small>усього</small>
        </article>
        <article className="is-active">
          <strong>{activeCount}</strong>
          <small>активні</small>
        </article>
        <article>
          <strong>{adminCount}</strong>
          <small>я адмін</small>
        </article>
        <article className={setupCount > 0 ? "needs-attention" : ""}>
          <strong>{setupCount}</strong>
          <small>увага</small>
        </article>
      </section>

      <label className="search-field groups-v2-search">
        <Search size={19} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Знайти групу"
          type="search"
        />
      </label>

      <div className="groups-filter-scroll" aria-label="Фільтри груп">
        {filters.map((item) => (
          <button
            className={filter === item.id ? "is-active" : ""}
            key={item.id}
            type="button"
            onClick={() => setFilter(item.id)}
          >
            {item.id === "favorite" ? <Star size={14} /> : null}
            {item.id === "active" ? <Activity size={14} /> : null}
            {item.label}
          </button>
        ))}
      </div>

      <div className="groups-v2-toolbar">
        <div>
          <strong>{visibleGroups.length}</strong>
          <span>{visibleGroups.length === 1 ? "група" : "груп"}</span>
        </div>
        <label className="select-pill groups-sort">
          <SlidersHorizontal size={16} />
          <select value={sort} onChange={(event) => setSort(event.target.value as SortMode)}>
            <option value="smart">Розумний порядок</option>
            <option value="activity">Найактивніші</option>
            <option value="recent">Остання активність</option>
            <option value="trend">Найкращий тренд</option>
            <option value="xp">Найбільше XP</option>
          </select>
        </label>
      </div>

      {visibleGroups.length > 0 ? (
        <div className="groups-v2-list">
          {visibleGroups.map((group) => (
            <GroupCard
              group={group}
              key={group.telegram_chat_id}
              onOpen={onOpenGroup}
              onToggleFavorite={(item, nextValue) => void toggleFavorite(item, nextValue)}
              favoriteBusy={favoriteBusy === group.telegram_chat_id}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title={groups.length === 0 ? "Поки немає груп" : "Нічого не знайдено"}
          description={
            groups.length === 0
              ? "Додай ChatPulse до Telegram-групи, і тут з’явиться її пульс."
              : "Спробуй інший пошук або обери фільтр «Усі»."
          }
          actionLabel="Оновити"
          onAction={onRefresh}
        />
      )}
    </div>
  );
}
