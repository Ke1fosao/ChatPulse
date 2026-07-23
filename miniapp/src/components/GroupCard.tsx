import {
  ArrowUpRight,
  ChevronRight,
  MessageCircle,
  ShieldCheck,
  Star,
  Trophy,
} from "lucide-react";
import type { CSSProperties } from "react";
import type { GroupsV2CardData } from "../api/groups-v2";
import { isGroupsV2Card } from "../api/groups-v2";
import type { GroupCardData } from "../api/types";
import { haptic } from "../telegram/sdk";

interface GroupCardProps {
  group: GroupCardData | GroupsV2CardData;
  onOpen(group: GroupCardData): void;
  onToggleFavorite?(group: GroupsV2CardData, nextValue: boolean): void;
  favoriteBusy?: boolean;
}

function statusFallback(group: GroupCardData) {
  return group.period.messages_count > 0
    ? { id: "active", label: "Активна", tone: "success" }
    : { id: "quiet", label: "Тиха", tone: "neutral" };
}

export function GroupCard({
  group,
  onOpen,
  onToggleFavorite,
  favoriteBusy = false,
}: GroupCardProps) {
  const enhanced = isGroupsV2Card(group);
  const status = enhanced ? group.status : statusFallback(group);
  const messages = enhanced ? group.messages_7d : group.period.messages_count;
  const today = enhanced ? group.messages_today : null;
  const hue = Math.abs(group.telegram_chat_id) % 360;
  const style = { "--group-hue": hue } as CSSProperties;

  return (
    <article className={`group-card-v2 group-card-v2--${status.tone}`} style={style}>
      <button
        className="group-card-v2__open"
        type="button"
        onClick={() => {
          haptic("medium");
          onOpen(group);
        }}
        aria-label={`Відкрити групу ${group.title}`}
      >
        <span className="group-avatar-v2" aria-hidden="true">
          {group.initials}
        </span>

        <span className="group-card-v2__content">
          <span className="group-card-v2__heading">
            <strong>{group.title}</strong>
            <span className={`group-status group-status--${status.tone}`}>
              <i /> {status.label}
            </span>
          </span>

          {enhanced && group.attention_reason ? (
            <span className="group-card-v2__attention">{group.attention_reason}</span>
          ) : (
            <span className="group-card-v2__metrics">
              <span>
                <Trophy size={14} /> #{group.rank ?? "—"}
              </span>
              <span>
                <MessageCircle size={14} /> {messages} за 7 днів
              </span>
              {today !== null ? <span>{today} сьогодні</span> : null}
            </span>
          )}

          <span className="group-card-v2__footer">
            {group.is_admin ? (
              <span className="group-admin-pill">
                <ShieldCheck size={13} /> Адмін
              </span>
            ) : (
              <span>Твоя позиція у групі</span>
            )}
            <span
              className={`group-trend ${group.trend !== null && group.trend !== undefined && group.trend < 0 ? "is-negative" : ""}`}
            >
              {group.trend === null || group.trend === undefined
                ? "Нові дані"
                : `${group.trend >= 0 ? "+" : ""}${group.trend}%`}
              <ArrowUpRight size={13} />
            </span>
          </span>
        </span>

        <ChevronRight className="group-card-v2__chevron" size={20} />
      </button>

      {enhanced && onToggleFavorite ? (
        <button
          className={`group-favorite ${group.is_favorite ? "is-active" : ""}`}
          type="button"
          disabled={favoriteBusy}
          aria-label={
            group.is_favorite
              ? `Прибрати ${group.title} з обраного`
              : `Додати ${group.title} в обране`
          }
          onClick={() => {
            haptic("light");
            onToggleFavorite(group, !group.is_favorite);
          }}
        >
          <Star size={17} fill={group.is_favorite ? "currentColor" : "none"} />
        </button>
      ) : null}
    </article>
  );
}
