import { Search, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import type { GroupCardData } from "../../api/types";
import { EmptyState } from "../../components/EmptyState";
import { GroupCard } from "../../components/GroupCard";

interface GroupsPageProps {
  groups: GroupCardData[];
  onOpenGroup(group: GroupCardData): void;
  onRefresh(): void;
}

type SortMode = "activity" | "xp" | "level" | "recent";

export function GroupsPage({ groups, onOpenGroup, onRefresh }: GroupsPageProps) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortMode>("activity");
  const [adminsOnly, setAdminsOnly] = useState(false);

  const visibleGroups = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("uk-UA");
    return groups
      .filter((group) => !adminsOnly || group.is_admin)
      .filter((group) => group.title.toLocaleLowerCase("uk-UA").includes(normalized))
      .sort((left, right) => {
        if (sort === "xp") return right.xp_total - left.xp_total;
        if (sort === "level") return right.level - left.level;
        if (sort === "recent") {
          return Date.parse(right.last_activity_at) - Date.parse(left.last_activity_at);
        }
        return right.period.xp_earned - left.period.xp_earned;
      });
  }, [adminsOnly, groups, query, sort]);

  return (
    <div className="page">
      <header className="page-heading">
        <p className="eyebrow">Усі твої чати</p>
        <h2>Мої групи</h2>
        <p>Перемикайся між групами й дивись, де зараз найбільший пульс.</p>
      </header>

      <label className="search-field">
        <Search size={19} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Пошук за назвою"
          type="search"
        />
      </label>

      <div className="filter-row">
        <label className="select-pill">
          <SlidersHorizontal size={16} />
          <select value={sort} onChange={(event) => setSort(event.target.value as SortMode)}>
            <option value="activity">За активністю</option>
            <option value="xp">За XP</option>
            <option value="level">За рівнем</option>
            <option value="recent">Нещодавні</option>
          </select>
        </label>
        <button
          className={`filter-chip ${adminsOnly ? "is-active" : ""}`}
          type="button"
          onClick={() => setAdminsOnly((value) => !value)}
        >
          Я адміністратор
        </button>
      </div>

      {visibleGroups.length > 0 ? (
        <div className="stack">
          {visibleGroups.map((group) => (
            <GroupCard group={group} key={group.telegram_chat_id} onOpen={onOpenGroup} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="Груп не знайдено"
          description="Зміни фільтри або додай ChatPulse до нової Telegram-групи."
          actionLabel="Оновити"
          onAction={onRefresh}
        />
      )}
    </div>
  );
}
