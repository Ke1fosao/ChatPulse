import { Crown, Medal } from "lucide-react";
import type { RankingRow } from "../api/types";

interface LeaderboardProps {
  rows: RankingRow[];
  compact?: boolean;
}

export function Leaderboard({ rows, compact = false }: LeaderboardProps) {
  if (rows.length === 0) {
    return <div className="empty-inline">Рейтинг з’явиться після нової активності</div>;
  }

  return (
    <div className={`leaderboard ${compact ? "leaderboard--compact" : ""}`}>
      {rows.map((row) => (
        <article
          className={`leaderboard-row ${row.is_current_user ? "is-current" : ""}`}
          key={row.telegram_user_id}
        >
          <span className={`rank rank--${Math.min(row.rank, 4)}`}>
            {row.rank === 1 ? (
              <Crown size={19} />
            ) : row.rank <= 3 ? (
              <Medal size={18} />
            ) : (
              row.rank
            )}
          </span>
          <span className="leader-avatar">{row.display_name.slice(0, 1).toUpperCase()}</span>
          <span className="leader-name">
            <strong>{row.display_name}</strong>
            <small>{row.username ? `@${row.username}` : "учасник"}</small>
          </span>
          <strong className="leader-value">{row.value.toLocaleString("uk-UA")}</strong>
        </article>
      ))}
    </div>
  );
}
