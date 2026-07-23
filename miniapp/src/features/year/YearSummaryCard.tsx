import { Award, CalendarDays, Flame, MessageCircleMore, RefreshCw, Sparkles, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import type { AccountAccess } from "../../api/types";
import { premiumApi } from "../../premium/premiumApi";
import type { YearSummaryPayload } from "../../premium/types";
import { VipUpgradeCard } from "../../premium/VipUpgradeCard";

interface YearSummaryCardProps {
  account: AccountAccess;
  trialAvailable: boolean;
  onOpenVip(source: string, featureKey?: string | null): void;
}

const months = [
  "січень",
  "лютий",
  "березень",
  "квітень",
  "травень",
  "червень",
  "липень",
  "серпень",
  "вересень",
  "жовтень",
  "листопад",
  "грудень",
];

export function YearSummaryCard({
  account,
  trialAvailable,
  onOpenVip,
}: YearSummaryCardProps) {
  const unlocked =
    account.is_owner ||
    account.entitlements.includes("premium.all") ||
    account.entitlements.includes("profile.premium_card");
  const year = new Date().getFullYear();
  const [data, setData] = useState<YearSummaryPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!unlocked) return;
    setLoading(true);
    setError("");
    void premiumApi
      .yearSummary(year)
      .then(setData)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Не вдалося завантажити рік."))
      .finally(() => setLoading(false));
  }, [unlocked, year]);

  if (!unlocked) {
    return (
      <section className="section-block year-summary-section">
        <div className="section-heading">
          <div><p className="eyebrow">Персональний підсумок</p><h2>Мій рік у ChatPulse</h2></div>
          <Sparkles size={21} />
        </div>
        <VipUpgradeCard
          title="Мій рік у ChatPulse"
          description="Побач повідомлення, XP, найкращий місяць, серію та нагороди за рік."
          source="year_summary"
          featureKey="profile.premium_card"
          trialAvailable={trialAvailable}
          onOpen={onOpenVip}
          preview={
            <div className="year-summary-preview">
              <span>12 480</span><span>8 920 XP</span><span>137 днів</span>
            </div>
          }
        />
      </section>
    );
  }

  return (
    <section className="section-block year-summary-section year-summary-section--active">
      <div className="section-heading">
        <div><p className="eyebrow">Персональний підсумок</p><h2>Мій рік у ChatPulse</h2></div>
        <span className="count-pill">{year}</span>
      </div>
      {loading && !data ? <div className="loading-panel"><RefreshCw className="spin" /> Збираємо рік…</div> : null}
      {error ? <div className="vip-error">{error}</div> : null}
      {data ? (
        <article className="year-summary-card panel">
          <div className="year-summary-card__hero">
            <span><Sparkles size={22} /></span>
            <div><p>Твій цифровий рік</p><strong>{data.year}</strong></div>
            <em>{data.active_days} активних днів</em>
          </div>
          <div className="year-summary-card__grid">
            <div><MessageCircleMore size={18} /><strong>{data.messages_count.toLocaleString("uk-UA")}</strong><span>повідомлень</span></div>
            <div><Zap size={18} /><strong>{data.xp_earned.toLocaleString("uk-UA")} XP</strong><span>зароблено</span></div>
            <div><Flame size={18} /><strong>{data.best_streak} дн.</strong><span>найкраща серія</span></div>
            <div><Award size={18} /><strong>{data.achievements_count}</strong><span>досягнень</span></div>
          </div>
          <div className="year-summary-card__footer">
            <CalendarDays size={17} />
            <span>Найкращий місяць</span>
            <strong>{data.top_month ? months[data.top_month - 1] : "ще визначається"}</strong>
          </div>
        </article>
      ) : null}
    </section>
  );
}
