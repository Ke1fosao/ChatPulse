import {
  Crown,
  Flame,
  Heart,
  Medal,
  MessageCircleMore,
  Reply,
  Star,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import type { ReactNode } from "react";
import type { GroupRankingPayload, GroupRankingRow } from "../../api/groups-v2";
import type { Metric } from "../../api/types";

interface GroupRankingTabProps {
  data: GroupRankingPayload;
  metric: Metric;
  onMetricChange(metric: Metric): void;
}

const metrics: Array<{ id: Metric; label: string; icon: ReactNode }> = [
  { id: "xp", label: "XP", icon: <Zap size={14} /> },
  { id: "messages", label: "Повідомлення", icon: <MessageCircleMore size={14} /> },
  { id: "reactions", label: "Реакції", icon: <Heart size={14} /> },
  { id: "replies", label: "Відповіді", icon: <Reply size={14} /> },
  { id: "streak", label: "Серія", icon: <Flame size={14} /> },
];

function metricSuffix(metric: Metric): string {
  if (metric === "xp") return "XP";
  if (metric === "streak") return "дн.";
  return "";
}

function RankingRowCard({ row, metric, pinned = false }: { row: GroupRankingRow; metric: Metric; pinned?: boolean }) {
  return (
    <article
      className={`group-ranking-row ${row.is_current_user ? "is-current" : ""} ${pinned ? "is-pinned" : ""}`}
    >
      <span className={`rank rank--${Math.min(row.rank, 4)}`}>
        {row.rank === 1 ? <Crown size={19} /> : row.rank <= 3 ? <Medal size={18} /> : row.rank}
      </span>
      <span className="leader-avatar">{row.display_name.slice(0, 1).toUpperCase()}</span>
      <span className="group-ranking-row__identity">
        <span>
          <strong>{row.display_name}</strong>
          {row.account_plan === "owner" ? (
            <i className="ranking-plan-badge is-owner"><Crown size={10} /> OWNER</i>
          ) : row.account_plan === "vip" ? (
            <i className="ranking-plan-badge is-vip"><Star size={10} /> VIP</i>
          ) : null}
        </span>
        <small>{pinned ? "Твоя позиція" : row.username ? `@${row.username}` : "учасник"}</small>
      </span>
      <span className="group-ranking-row__score">
        <strong>
          {row.value.toLocaleString("uk-UA")} {metricSuffix(metric)}
        </strong>
        {row.rank_change ? (
          <small className={row.rank_change > 0 ? "is-up" : "is-down"}>
            {row.rank_change > 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
            {row.rank_change > 0 ? `+${row.rank_change}` : row.rank_change}
          </small>
        ) : (
          <small>без змін</small>
        )}
      </span>
    </article>
  );
}

export function GroupRankingTab({ data, metric, onMetricChange }: GroupRankingTabProps) {
  const currentVisible = data.current_user
    ? data.rows.some((row) => row.telegram_user_id === data.current_user?.telegram_user_id)
    : true;

  return (
    <div className="group-tab-content group-ranking-tab">
      <section className="group-ranking-intro">
        <div>
          <p className="eyebrow">Лідери групи</p>
          <h2>Рейтинг учасників</h2>
          <p>Перемикай показник, не перезавантажуючи всю сторінку групи.</p>
        </div>
        <span><Crown size={23} /></span>
      </section>

      <div className="group-metric-scroll" aria-label="Показник рейтингу">
        {metrics.map((item) => (
          <button
            className={metric === item.id ? "is-active" : ""}
            key={item.id}
            type="button"
            onClick={() => onMetricChange(item.id)}
          >
            {item.icon} {item.label}
          </button>
        ))}
      </div>

      {!currentVisible && data.current_user ? (
        <section className="group-current-rank">
          <p className="eyebrow">Твоя позиція</p>
          <RankingRowCard row={data.current_user} metric={metric} pinned />
        </section>
      ) : null}

      {data.rows.length ? (
        <section className="group-ranking-list">
          {data.rows.map((row) => (
            <RankingRowCard key={row.telegram_user_id} row={row} metric={metric} />
          ))}
        </section>
      ) : (
        <div className="group-tab-empty">
          <Crown size={26} />
          <strong>Рейтинг ще формується</strong>
          <span>Він з’явиться після нової активності в групі.</span>
        </div>
      )}
    </div>
  );
}
