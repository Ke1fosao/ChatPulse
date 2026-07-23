import {
  Activity,
  ArrowRight,
  Award,
  BarChart3,
  Crown,
  FileChartColumn,
  Flame,
  MessageCircleMore,
  Send,
  Share2,
  Sparkles,
  TrendingUp,
  Users,
} from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import type { GroupInsight, GroupOverviewPayload } from "../../api/groups-v2";
import { openTelegramLink } from "../../telegram/sdk";

interface GroupOverviewTabProps {
  data: GroupOverviewPayload;
  actionBusy: string | null;
  onOpenRanking(): void;
  onShare(): void;
  onSendReport(): void;
  onTogglePaused(): void;
}

const insightIcons: Record<string, ReactNode> = {
  ranking: <TrendingUp size={17} />,
  achievement: <Award size={17} />,
  record: <BarChart3 size={17} />,
  streak: <Flame size={17} />,
  leader: <Crown size={17} />,
  report: <FileChartColumn size={17} />,
  summary: <Activity size={17} />,
};

function InsightCard({ insight }: { insight: GroupInsight }) {
  return (
    <article className={`group-insight group-insight--${insight.kind}`}>
      <span>{insightIcons[insight.kind] ?? <Sparkles size={17} />}</span>
      <div>
        <strong>{insight.title}</strong>
        <small>{insight.description}</small>
      </div>
    </article>
  );
}

export function GroupOverviewTab({
  data,
  actionBusy,
  onOpenRanking,
  onShare,
  onSendReport,
  onTogglePaused,
}: GroupOverviewTabProps) {
  const progress = Math.min(
    100,
    Math.round((data.personal_progress.progress / Math.max(data.personal_progress.needed, 1)) * 100),
  );
  const paused = data.settings.is_paused;

  return (
    <div className="group-tab-content group-overview-tab">
      <section className={`group-pulse-card group-pulse-card--${data.pulse.tone}`}>
        <div
          className="group-pulse-ring"
          style={{ "--pulse-score": `${data.pulse.score * 3.6}deg` } as CSSProperties}
          aria-label={`Пульс групи ${data.pulse.score} зі 100`}
        >
          <span>
            <strong>{data.pulse.score}</strong>
            <small>зі 100</small>
          </span>
        </div>
        <div className="group-pulse-copy">
          <p className="eyebrow">Пульс групи</p>
          <h2>{data.pulse.label}</h2>
          {data.pulse.positive ? <p className="is-positive">{data.pulse.positive}</p> : null}
          {data.pulse.negative ? <p className="is-negative">{data.pulse.negative}</p> : null}
        </div>
        <div className="group-pulse-components">
          <span><i style={{ width: `${data.pulse.components.messages}%` }} />Повідомлення</span>
          <span><i style={{ width: `${data.pulse.components.members}%` }} />Учасники</span>
          <span><i style={{ width: `${data.pulse.components.engagement}%` }} />Взаємодія</span>
          <span><i style={{ width: `${data.pulse.components.continuity}%` }} />Стабільність</span>
        </div>
      </section>

      <section className="group-personal-card">
        <div className="group-personal-card__top">
          <div>
            <p className="eyebrow">Твій результат</p>
            <h2>Рівень {data.personal_progress.level} · {data.personal_progress.tier}</h2>
          </div>
          <span className="group-personal-rank">
            <strong>#{data.personal_progress.rank ?? "—"}</strong>
            {data.personal_progress.rank_change ? (
              <small className={data.personal_progress.rank_change > 0 ? "is-up" : "is-down"}>
                {data.personal_progress.rank_change > 0 ? "+" : ""}
                {data.personal_progress.rank_change}
              </small>
            ) : null}
          </span>
        </div>
        <div className="group-personal-xp">
          <span>{data.personal_progress.xp_total.toLocaleString("uk-UA")} XP</span>
          <small>{data.personal_progress.progress} / {data.personal_progress.needed}</small>
        </div>
        <div className="group-personal-progress"><span style={{ width: `${progress}%` }} /></div>
        <div className="group-personal-meta">
          <span><Flame size={15} /> {data.personal_progress.current_streak} днів</span>
          <span><MessageCircleMore size={15} /> {data.personal_progress.period.messages_count} повідомлень</span>
        </div>
      </section>

      <section className="group-overview-section">
        <div className="section-heading">
          <div><p className="eyebrow">Топ учасників</p><h2>Лідери періоду</h2></div>
          <button className="text-action" type="button" onClick={onOpenRanking}>
            Увесь рейтинг <ArrowRight size={15} />
          </button>
        </div>
        {data.top_participants.length ? (
          <div className="group-top-three">
            {data.top_participants.slice(0, 3).map((row) => (
              <article key={row.telegram_user_id} className={row.is_current_user ? "is-current" : ""}>
                <span className={`rank rank--${Math.min(row.rank, 4)}`}>
                  {row.rank === 1 ? <Crown size={18} /> : row.rank}
                </span>
                <i>{row.display_name.slice(0, 1).toUpperCase()}</i>
                <strong>{row.display_name}</strong>
                <small>{row.value.toLocaleString("uk-UA")} XP</small>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-inline">Рейтинг з’явиться після нової активності</div>
        )}
      </section>

      <section className="group-overview-section">
        <div className="section-heading">
          <div><p className="eyebrow">Події</p><h2>Що нового</h2></div>
          <Sparkles size={20} />
        </div>
        <div className="group-insights-list">
          {data.insights.map((insight) => <InsightCard key={insight.id} insight={insight} />)}
        </div>
      </section>

      {data.top_message ? (
        <button
          className="group-highlight-card"
          type="button"
          disabled={!data.top_message.url}
          onClick={() => data.top_message?.url && openTelegramLink(data.top_message.url)}
        >
          <span><Send size={20} /></span>
          <div>
            <p className="eyebrow">Повідомлення періоду</p>
            <strong>{data.top_message.display_name}</strong>
            <small>{data.top_message.reactions_count} реакцій · текст не зберігається</small>
          </div>
          <ArrowRight size={18} />
        </button>
      ) : null}

      <section className="group-quick-actions">
        {data.group.telegram_url ? (
          <button type="button" onClick={() => openTelegramLink(data.group.telegram_url!)}>
            <MessageCircleMore size={18} /> Відкрити групу
          </button>
        ) : null}
        <button type="button" onClick={onShare}>
          <Share2 size={18} /> Поділитися
        </button>
        <button type="button" onClick={onOpenRanking}>
          <Users size={18} /> Рейтинг
        </button>
      </section>

      {data.capabilities?.is_admin ? (
        <section className="group-admin-actions">
          <div>
            <p className="eyebrow">Швидкі дії адміністратора</p>
            <strong>Керування без зайвих переходів</strong>
          </div>
          <button type="button" disabled={Boolean(actionBusy)} onClick={onSendReport}>
            <FileChartColumn size={17} />
            {actionBusy === "report" ? "Надсилаємо…" : "Надіслати звіт"}
          </button>
          <button
            className={paused ? "is-resume" : "is-pause"}
            type="button"
            disabled={Boolean(actionBusy)}
            onClick={onTogglePaused}
          >
            <Activity size={17} />
            {actionBusy === "pause"
              ? "Зберігаємо…"
              : paused
                ? "Відновити аналітику"
                : "Призупинити аналітику"}
          </button>
        </section>
      ) : null}
    </div>
  );
}
