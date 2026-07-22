import { Pause, Play, Radio, RefreshCw, Search, Send, Users } from "lucide-react";
import type { OwnerGroup } from "./types";

interface OwnerGroupsProps {
  groups: OwnerGroup[];
  total: number;
  loading: boolean;
  query: string;
  onQueryChange(value: string): void;
  onRefresh(): void;
  onUpdate(chatId: number, values: Partial<OwnerGroup>): Promise<void>;
}

export function OwnerGroups({
  groups,
  total,
  loading,
  query,
  onQueryChange,
  onRefresh,
  onUpdate,
}: OwnerGroupsProps) {
  return (
    <div className="owner-page">
      <header className="owner-page-heading">
        <div>
          <p>Системне керування</p>
          <h2>Групи</h2>
        </div>
        <span className="owner-count">{total}</span>
      </header>

      <section className="owner-toolbar owner-toolbar--inline">
        <label className="owner-search">
          <Search size={17} />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Знайти групу"
          />
        </label>
        <button type="button" className="owner-square-button" aria-label="Оновити групи" onClick={onRefresh}>
          <RefreshCw size={18} />
        </button>
      </section>

      <section className="owner-list" aria-busy={loading}>
        {groups.length === 0 ? (
          <div className="owner-empty">{loading ? "Завантаження груп…" : "Груп не знайдено."}</div>
        ) : groups.map((group) => (
          <article className="owner-group-card" key={group.telegram_chat_id}>
            <div className="owner-group-card__head">
              <span><Radio size={19} /></span>
              <div>
                <strong>{group.title}</strong>
                <p>{group.username ? `@${group.username}` : `ID ${group.telegram_chat_id}`}</p>
              </div>
              <em className={group.is_active ? "is-live" : ""}>{group.is_active ? "ACTIVE" : "OFF"}</em>
            </div>
            <div className="owner-group-card__stats">
              <span><Users size={14} /> {group.members_count}</span>
              <span><Send size={14} /> {group.weekly_reports_enabled ? "Звіти увімкнено" : "Звіти вимкнено"}</span>
              <span>{group.report_card_theme.replaceAll("_", " ")}</span>
            </div>
            <div className="owner-group-card__controls">
              <button
                type="button"
                className={group.is_paused ? "is-warning" : ""}
                onClick={() => void onUpdate(group.telegram_chat_id, { is_paused: !group.is_paused })}
              >
                {group.is_paused ? <Play size={16} /> : <Pause size={16} />}
                {group.is_paused ? "Продовжити" : "Пауза"}
              </button>
              <button
                type="button"
                onClick={() => void onUpdate(group.telegram_chat_id, {
                  weekly_reports_enabled: !group.weekly_reports_enabled,
                })}
              >
                <Send size={16} />
                {group.weekly_reports_enabled ? "Вимкнути звіти" : "Увімкнути звіти"}
              </button>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
