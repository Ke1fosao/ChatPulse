import {
  ArrowLeft,
  Award,
  BarChart3,
  Flame,
  Heart,
  Image,
  MessageCircle,
  Reply,
  Send,
  Settings2,
  Shield,
  ShieldCheck,
  Trophy,
  Users,
  Zap,
} from "lucide-react";
import { useState } from "react";
import type { GroupDashboard, GroupSettings, Period } from "../../api/types";
import { ActivityChart } from "../../components/ActivityChart";
import { Heatmap } from "../../components/Heatmap";
import { Leaderboard } from "../../components/Leaderboard";
import { StatCard } from "../../components/StatCard";
import { usePremium } from "../../premium/PremiumContext";
import { openTelegramLink } from "../../telegram/sdk";
import { GroupSettingsPanel } from "../admin/GroupSettingsPanel";
import { PremiumAnalytics } from "./PremiumAnalytics";

interface GroupDashboardPageProps {
  data: GroupDashboard;
  onBack(): void;
  onPeriodChange(period: Period): void;
  onSaveSettings(settings: Partial<GroupSettings>): Promise<GroupSettings>;
  onReset(): Promise<void>;
}

const periods: Array<{ id: Period; label: string }> = [
  { id: "week", label: "7 днів" },
  { id: "month", label: "30 днів" },
  { id: "all", label: "Весь час" },
];

export function GroupDashboardPage({
  data,
  onBack,
  onPeriodChange,
  onSaveSettings,
  onReset,
}: GroupDashboardPageProps) {
  const [chartMetric, setChartMetric] = useState<"xp" | "messages" | "reactions" | "replies">("messages");
  const [showSettings, setShowSettings] = useState(false);
  const summary = data.overview.current;
  const isAdmin = Boolean(data.capabilities?.is_admin);
  const premium = usePremium();

  if (showSettings && isAdmin) {
    return (
      <div className="page group-dashboard group-dashboard--settings">
        <GroupSettingsPanel
          chatId={data.group.telegram_chat_id}
          settings={data.settings}
          onSave={onSaveSettings}
          onReset={onReset}
          onBack={() => setShowSettings(false)}
        />
      </div>
    );
  }

  return (
    <div className="page group-dashboard">
      <header className="group-hero panel">
        <button className="icon-button" type="button" onClick={onBack} aria-label="Назад"><ArrowLeft size={20} /></button>
        <span className="group-avatar group-avatar--large">{data.group.initials}</span>
        <div className="group-hero__copy"><p className="eyebrow">Пульс групи</p><h2>{data.group.title}</h2><span>{data.group.timezone}</span></div>
      </header>

      {isAdmin ? (
        <section className="group-admin-banner">
          <span className="group-admin-banner__icon"><ShieldCheck size={21} /></span>
          <div><p className="eyebrow">Ваш доступ</p><strong>Ви адміністратор цієї групи</strong><small>Можете керувати звітами, збором даних та оформленням.</small></div>
          <button type="button" onClick={() => setShowSettings(true)}><Settings2 size={17} /> Керувати групою</button>
        </section>
      ) : null}

      <div className="segmented-control" aria-label="Період статистики">
        {periods.map((period) => (
          <button className={data.period === period.id ? "is-active" : ""} key={period.id} type="button" onClick={() => onPeriodChange(period.id)}>{period.label}</button>
        ))}
      </div>

      <section className="stats-grid">
        <StatCard accent icon={<MessageCircle size={19} />} label="Повідомлення" value={summary.messages_count} trend={data.overview.trends.messages_count} />
        <StatCard icon={<Heart size={19} />} label="Реакції" value={summary.reactions_received} trend={data.overview.trends.reactions_received} />
        <StatCard icon={<Reply size={19} />} label="Відповіді" value={summary.replies_count} trend={data.overview.trends.replies_count} />
        <StatCard icon={<Image size={19} />} label="Медіа" value={summary.media_count} trend={data.overview.trends.media_count} />
        <StatCard icon={<Users size={19} />} label="Активні" value={summary.active_members} trend={data.overview.trends.active_members} />
        <StatCard icon={<Zap size={19} />} label="XP групи" value={summary.xp_earned} trend={data.overview.trends.xp_earned} />
      </section>

      <section className="panel personal-progress">
        <div className="section-heading"><div><p className="eyebrow">Твій результат</p><h2>Рівень {data.personal_progress.level} · {data.personal_progress.tier}</h2></div><strong>#{data.personal_progress.rank ?? "—"}</strong></div>
        <div className="personal-progress__xp"><span>{data.personal_progress.xp_total.toLocaleString("uk-UA")} XP</span><small>{data.personal_progress.progress} / {data.personal_progress.needed}</small></div>
        <div className="hero-progress"><span style={{ width: `${Math.min(100, Math.round((data.personal_progress.progress / data.personal_progress.needed) * 100))}%` }} /></div>
        <div className="personal-progress__badges"><span><Flame size={16} /> {data.personal_progress.current_streak} днів</span><span><Trophy size={16} /> рекорд {data.personal_progress.longest_streak}</span><span><Shield size={16} /> захист {data.personal_progress.protection_left}</span></div>
      </section>

      <section className="chart-wrapper">
        <div className="metric-tabs">
          {([ ["messages", "Повідомлення"], ["xp", "XP"], ["reactions", "Реакції"], ["replies", "Відповіді"] ] as const).map(([metric, label]) => (
            <button className={chartMetric === metric ? "is-active" : ""} key={metric} type="button" onClick={() => setChartMetric(metric)}>{label}</button>
          ))}
        </div>
        <ActivityChart data={data.activity_series} metric={chartMetric} title="Активність групи" />
      </section>

      <PremiumAnalytics account={premium.account} chatId={data.group.telegram_chat_id} trialAvailable={premium.trialAvailable} onOpenVip={premium.openVip} />
      <Heatmap data={data.heatmap} />

      {data.top_message ? (
        <button className="top-message-card" type="button" onClick={() => data.top_message?.url && openTelegramLink(data.top_message.url)}>
          <span><Send size={21} /></span><div><p className="eyebrow">Повідомлення періоду</p><strong>{data.top_message.display_name}</strong><small>{data.top_message.reactions_count} реакцій · без збереження тексту</small></div><ArrowLeft className="rotate-180" size={19} />
        </button>
      ) : null}

      <section className="panel"><div className="section-heading"><div><p className="eyebrow">Лідери</p><h2>Топ за XP</h2></div><BarChart3 size={22} /></div><Leaderboard rows={data.leaderboard} /></section>

      <section className="section-block">
        <div className="section-heading"><div><p className="eyebrow">Характер чату</p><h2>Номінації</h2></div><Award size={22} /></div>
        <div className="nomination-grid">{data.nominations.map((nomination) => <article className="nomination-card" key={nomination.metric}><span>{nomination.title.split(" ")[0]}</span><strong>{nomination.display_name}</strong><small>{nomination.value.toLocaleString("uk-UA")}</small></article>)}</div>
      </section>
    </div>
  );
}
