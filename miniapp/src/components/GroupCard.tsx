import { ChevronRight, Flame, MessageCircle, Trophy } from "lucide-react";
import type { GroupCardData } from "../api/types";
import { haptic } from "../telegram/sdk";

interface GroupCardProps {
  group: GroupCardData;
  onOpen(group: GroupCardData): void;
}

export function GroupCard({ group, onOpen }: GroupCardProps) {
  return (
    <button
      className="group-card"
      type="button"
      onClick={() => {
        haptic("medium");
        onOpen(group);
      }}
    >
      <span className="group-avatar">{group.initials}</span>
      <span className="group-card__main">
        <span className="group-card__title-row">
          <strong>{group.title}</strong>
          {group.is_admin ? <em>ADMIN</em> : null}
        </span>
        <span className="group-card__meta">
          <span>
            <Trophy size={14} /> #{group.rank ?? "—"}
          </span>
          <span>
            <Flame size={14} /> {group.current_streak} дн.
          </span>
          <span>
            <MessageCircle size={14} /> {group.period.messages_count}
          </span>
        </span>
        <span className="group-card__progress">
          <span style={{ width: `${Math.min(100, Math.max(8, group.level * 4))}%` }} />
        </span>
      </span>
      <span className="group-card__side">
        <strong>{group.period.xp_earned} XP</strong>
        <small className={group.trend && group.trend < 0 ? "is-negative" : ""}>
          {group.trend === null || group.trend === undefined
            ? "—"
            : `${group.trend >= 0 ? "+" : ""}${group.trend}%`}
        </small>
        <ChevronRight size={19} />
      </span>
    </button>
  );
}
