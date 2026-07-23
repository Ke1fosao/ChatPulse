import {
  BarChart3,
  Heart,
  Image,
  MessageCircle,
  Reply,
  Users,
  Zap,
} from "lucide-react";
import { useState } from "react";
import type { GroupAnalyticsPayload } from "../../api/groups-v2";
import type { AccountAccess } from "../../api/types";
import { ActivityChart } from "../../components/ActivityChart";
import { Heatmap } from "../../components/Heatmap";
import { StatCard } from "../../components/StatCard";
import { PremiumAnalytics } from "./PremiumAnalytics";

interface GroupAnalyticsTabProps {
  data: GroupAnalyticsPayload;
  account: AccountAccess;
  trialAvailable: boolean;
  onOpenVip(source: string, featureKey?: string | null): void;
}

type ChartMetric = "messages" | "xp" | "reactions" | "replies";

const metricLabels: Array<[ChartMetric, string]> = [
  ["messages", "Повідомлення"],
  ["xp", "XP"],
  ["reactions", "Реакції"],
  ["replies", "Відповіді"],
];

export function GroupAnalyticsTab({
  data,
  account,
  trialAvailable,
  onOpenVip,
}: GroupAnalyticsTabProps) {
  const [chartMetric, setChartMetric] = useState<ChartMetric>("messages");
  const summary = data.overview.current;

  return (
    <div className="group-tab-content group-analytics-tab">
      <section className="group-analytics-intro">
        <div>
          <p className="eyebrow">Детальна картина</p>
          <h2>Аналітика групи</h2>
          <p>Усі цифри й графіки зібрані тут, а Огляд залишається легким.</p>
        </div>
        <span><BarChart3 size={23} /></span>
      </section>

      <section className="stats-grid group-analytics-stats">
        <StatCard
          accent
          icon={<MessageCircle size={19} />}
          label="Повідомлення"
          value={summary.messages_count}
          trend={data.overview.trends.messages_count}
        />
        <StatCard
          icon={<Heart size={19} />}
          label="Реакції"
          value={summary.reactions_received}
          trend={data.overview.trends.reactions_received}
        />
        <StatCard
          icon={<Reply size={19} />}
          label="Відповіді"
          value={summary.replies_count}
          trend={data.overview.trends.replies_count}
        />
        <StatCard
          icon={<Image size={19} />}
          label="Медіа"
          value={summary.media_count}
          trend={data.overview.trends.media_count}
        />
        <StatCard
          icon={<Users size={19} />}
          label="Активні"
          value={summary.active_members}
          trend={data.overview.trends.active_members}
        />
        <StatCard
          icon={<Zap size={19} />}
          label="XP групи"
          value={summary.xp_earned}
          trend={data.overview.trends.xp_earned}
        />
      </section>

      <section className="group-chart-section">
        <div className="group-metric-scroll" aria-label="Показник графіка">
          {metricLabels.map(([metric, label]) => (
            <button
              className={chartMetric === metric ? "is-active" : ""}
              key={metric}
              type="button"
              onClick={() => setChartMetric(metric)}
            >
              {label}
            </button>
          ))}
        </div>
        <ActivityChart data={data.activity_series} metric={chartMetric} title="Активність групи" />
      </section>

      <Heatmap data={data.heatmap} />

      {data.popular_reaction ? (
        <section className="group-popular-reaction">
          <span>{data.popular_reaction.emoji}</span>
          <div>
            <p className="eyebrow">Реакція періоду</p>
            <strong>{data.popular_reaction.count.toLocaleString("uk-UA")} використань</strong>
          </div>
        </section>
      ) : null}

      <PremiumAnalytics
        account={account}
        chatId={data.group.telegram_chat_id}
        trialAvailable={trialAvailable}
        onOpenVip={onOpenVip}
      />
    </div>
  );
}
