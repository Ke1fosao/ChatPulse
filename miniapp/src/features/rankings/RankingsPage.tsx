import { BarChart3, Medal, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import type {
  GroupCardData,
  Metric,
  Period,
  RankingPayload,
} from "../../api/types";
import { EmptyState } from "../../components/EmptyState";
import { Leaderboard } from "../../components/Leaderboard";

interface RankingsPageProps {
  groups: GroupCardData[];
  ranking: RankingPayload | null;
  loading: boolean;
  selectedGroupId: number | null;
  metric: Metric;
  period: Period;
  onGroupChange(chatId: number): void;
  onMetricChange(metric: Metric): void;
  onPeriodChange(period: Period): void;
  onRefresh(): void;
}

const metrics: Array<{ id: Metric; label: string }> = [
  { id: "xp", label: "XP" },
  { id: "messages", label: "Повідомлення" },
  { id: "reactions", label: "Реакції" },
  { id: "replies", label: "Відповіді" },
  { id: "streak", label: "Серія" },
];

export function RankingsPage({
  groups,
  ranking,
  loading,
  selectedGroupId,
  metric,
  period,
  onGroupChange,
  onMetricChange,
  onPeriodChange,
  onRefresh,
}: RankingsPageProps) {
  const [podiumReady, setPodiumReady] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => setPodiumReady(true), 80);
    return () => window.clearTimeout(timer);
  }, [ranking]);

  if (groups.length === 0) {
    return (
      <EmptyState
        title="Рейтинг ще порожній"
        description="Додай ChatPulse до групи, щоб змагатися за перше місце."
        actionLabel="Оновити"
        onAction={onRefresh}
      />
    );
  }

  const podium = ranking?.rows.slice(0, 3) ?? [];

  return (
    <div className="page rankings-page">
      <header className="page-heading page-heading--with-icon">
        <div>
          <p className="eyebrow">Хто задає темп</p>
          <h2>Рейтинг</h2>
          <p>Перемикай метрику й дивись, хто зараз на вершині.</p>
        </div>
        <span className="heading-icon"><BarChart3 /></span>
      </header>

      <label className="context-select panel">
        <span>Група</span>
        <select
          value={selectedGroupId ?? groups[0].telegram_chat_id}
          onChange={(event) => onGroupChange(Number(event.target.value))}
        >
          {groups.map((group) => (
            <option key={group.telegram_chat_id} value={group.telegram_chat_id}>
              {group.title}
            </option>
          ))}
        </select>
      </label>

      <div className="metric-tabs metric-tabs--scroll">
        {metrics.map((item) => (
          <button
            className={metric === item.id ? "is-active" : ""}
            key={item.id}
            type="button"
            onClick={() => onMetricChange(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="segmented-control segmented-control--small">
        {([
          ["week", "7 днів"],
          ["month", "30 днів"],
          ["all", "Весь час"],
        ] as const).map(([id, label]) => (
          <button
            className={period === id ? "is-active" : ""}
            key={id}
            type="button"
            onClick={() => onPeriodChange(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading-panel"><RefreshCw className="spin" /> Оновлюємо рейтинг…</div>
      ) : (
        <>
          <section className={`podium ${podiumReady ? "is-ready" : ""}`}>
            {[podium[1], podium[0], podium[2]].map((row, index) => {
              const place = index === 0 ? 2 : index === 1 ? 1 : 3;
              if (!row) return <div className="podium-slot is-empty" key={`empty-${place}`} />;
              return (
                <article className={`podium-slot podium-slot--${place}`} key={row.telegram_user_id}>
                  <span className="podium-avatar">{row.display_name.slice(0, 1).toUpperCase()}</span>
                  <span className="podium-place">
                    {place === 1 ? <Medal size={18} /> : place}
                  </span>
                  <strong>{row.display_name}</strong>
                  <small>{row.value.toLocaleString("uk-UA")}</small>
                </article>
              );
            })}
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Повний список</p>
                <h2>Таблиця лідерів</h2>
              </div>
            </div>
            <Leaderboard rows={ranking?.rows ?? []} />
            {ranking?.current_user && ranking.current_user.rank > 50 ? (
              <div className="pinned-rank">
                <span>Твоя позиція</span>
                <strong>#{ranking.current_user.rank}</strong>
                <small>{ranking.current_user.value.toLocaleString("uk-UA")}</small>
              </div>
            ) : null}
          </section>
        </>
      )}
    </div>
  );
}
