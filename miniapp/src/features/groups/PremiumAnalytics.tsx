import { BarChart3, Download, RefreshCw, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import type { AccountAccess } from "../../api/types";
import { ActivityChart } from "../../components/ActivityChart";
import { premiumApi } from "../../premium/premiumApi";
import type { PremiumAnalyticsPayload, PremiumAnalyticsPeriod } from "../../premium/types";
import { VipUpgradeCard } from "../../premium/VipUpgradeCard";
import { saveBlob, vipApi } from "../../vip/vipApi";

interface PremiumAnalyticsProps {
  account: AccountAccess;
  chatId: number;
  trialAvailable: boolean;
  onOpenVip(source: string, featureKey?: string | null): void;
}

const periods: Array<{ id: PremiumAnalyticsPeriod; label: string }> = [
  { id: "quarter", label: "90 днів" },
  { id: "half_year", label: "6 місяців" },
  { id: "year", label: "12 місяців" },
];

export function PremiumAnalytics({
  account,
  chatId,
  trialAvailable,
  onOpenVip,
}: PremiumAnalyticsProps) {
  const unlocked =
    account.is_owner ||
    account.entitlements.includes("premium.all") ||
    account.entitlements.includes("analytics.extended_history");
  const [period, setPeriod] = useState<PremiumAnalyticsPeriod>("quarter");
  const [data, setData] = useState<PremiumAnalyticsPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!unlocked) return;
    setLoading(true);
    setError("");
    void premiumApi
      .analytics(chatId, period, period === "quarter" ? "half_year" : "quarter")
      .then(setData)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Не вдалося завантажити."))
      .finally(() => setLoading(false));
  }, [chatId, period, unlocked]);

  if (!unlocked) {
    return (
      <section className="section-block premium-analytics-block">
        <div className="section-heading">
          <div><p className="eyebrow">VIP-аналітика</p><h2>Розширена історія</h2></div>
          <Sparkles size={21} />
        </div>
        <div className="metric-tabs premium-period-preview">
          {periods.map((item) => <button type="button" disabled key={item.id}>{item.label}</button>)}
        </div>
        <VipUpgradeCard
          title="Розширена аналітика"
          description="Дивись історію до року, порівнюй періоди та завантажуй звіти."
          source="group_analytics"
          featureKey="analytics.extended_history"
          trialAvailable={trialAvailable}
          onOpen={onOpenVip}
          preview={<div className="premium-chart-preview"><i /><i /><i /><i /><i /><i /></div>}
        />
      </section>
    );
  }

  const exportData = async (format: "csv" | "pdf") => {
    setLoading(true);
    try {
      const blob = await vipApi.exportGroup(chatId, format, "month");
      saveBlob(blob, `chatpulse-${chatId}.${format}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="section-block premium-analytics-block is-unlocked">
      <div className="section-heading">
        <div><p className="eyebrow">VIP-аналітика</p><h2>Розширена історія</h2></div>
        <BarChart3 size={21} />
      </div>
      <div className="metric-tabs metric-tabs--scroll">
        {periods.map((item) => (
          <button
            type="button"
            key={item.id}
            className={period === item.id ? "is-active" : ""}
            onClick={() => setPeriod(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {loading && !data ? <div className="premium-analytics-loading"><RefreshCw className="spin" /> Завантажуємо…</div> : null}
      {error ? <div className="vip-error">{error}</div> : null}
      {data ? (
        <>
          <div className="premium-summary-grid">
            <article><span>Повідомлення</span><strong>{data.overview.messages_count.toLocaleString("uk-UA")}</strong></article>
            <article><span>Активні</span><strong>{data.overview.active_members.toLocaleString("uk-UA")}</strong></article>
            <article><span>XP групи</span><strong>{data.overview.xp_earned.toLocaleString("uk-UA")}</strong></article>
          </div>
          <ActivityChart data={data.activity_series} metric="messages" title={`Активність за ${data.days} днів`} />
          <div className="premium-export-row">
            <span><Download size={17} /> Експорт звіту за 30 днів</span>
            <button type="button" disabled={loading} onClick={() => void exportData("csv")}>CSV</button>
            <button type="button" disabled={loading} onClick={() => void exportData("pdf")}>PDF</button>
          </div>
        </>
      ) : null}
    </section>
  );
}
