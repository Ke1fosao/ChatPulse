import {
  ArrowDownRight,
  ArrowUpRight,
  CalendarClock,
  ChevronRight,
  CircleDollarSign,
  Download,
  RefreshCw,
  RotateCcw,
  Search,
  Star,
  Users,
  WalletCards,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { notify } from "../telegram/sdk";
import { revenueApi, type RevenueFilters } from "./revenueApi";
import type {
  RevenuePlanPoint,
  RevenueSummary,
  RevenueTimelinePoint,
  RevenueTransaction,
  RevenueTransactionDetail,
} from "./types";

const planLabels: Record<string, string> = {
  trial_7d: "Trial · 7 днів",
  monthly_30d: "30 днів",
  quarter_90d: "90 днів",
  year_365d: "365 днів",
};

export function OwnerPayments() {
  const [days, setDays] = useState(30);
  const [summary, setSummary] = useState<RevenueSummary | null>(null);
  const [timeline, setTimeline] = useState<RevenueTimelinePoint[]>([]);
  const [plans, setPlans] = useState<RevenuePlanPoint[]>([]);
  const [transactions, setTransactions] = useState<RevenueTransaction[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<RevenueFilters>({ recurring: "all" });
  const [selected, setSelected] = useState<RevenueTransactionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const activeFilters = { ...filters, days };
      const [summaryPayload, timelinePayload, planPayload, transactionPayload] = await Promise.all([
        revenueApi.summary(days),
        revenueApi.timeline(days),
        revenueApi.plans(days),
        revenueApi.transactions(activeFilters),
      ]);
      setSummary(summaryPayload);
      setTimeline(timelinePayload);
      setPlans(planPayload);
      setTransactions(transactionPayload.items);
      setTotal(transactionPayload.total);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося завантажити оплати.");
      notify("error");
    } finally {
      setLoading(false);
    }
  }, [days, filters]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 220);
    return () => window.clearTimeout(timer);
  }, [load]);

  const openTransaction = async (paymentId: number) => {
    setBusy(`detail-${paymentId}`);
    try {
      setSelected(await revenueApi.detail(paymentId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося відкрити транзакцію.");
    } finally {
      setBusy("");
    }
  };

  const exportCsv = async () => {
    setBusy("export");
    try {
      const blob = await revenueApi.exportCsv({ ...filters, days });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "chatpulse-payments.csv";
      anchor.click();
      URL.revokeObjectURL(url);
      notify("success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося експортувати CSV.");
    } finally {
      setBusy("");
    }
  };

  const maxNet = Math.max(1, ...timeline.map((point) => point.net_stars));
  const totalPlanStars = Math.max(1, plans.reduce((sum, plan) => sum + plan.stars, 0));

  const metrics = useMemo(() => {
    if (!summary) return [];
    return [
      { label: "Stars сьогодні", value: `${summary.stars_today} ⭐`, note: "успішні оплати", icon: Star },
      { label: "Stars · 7 днів", value: `${summary.stars_7d} ⭐`, note: "чистий дохід", icon: ArrowUpRight },
      { label: "Stars · 30 днів", value: `${summary.stars_30d} ⭐`, note: `${summary.payments} оплат у фільтрі`, icon: CircleDollarSign },
      { label: "Stars · весь час", value: `${summary.stars_all_time} ⭐`, note: "без повернених", icon: WalletCards },
      { label: "MRR", value: `${summary.mrr_stars} ⭐`, note: `${summary.active_subscriptions} підписок`, icon: RotateCcw },
      { label: "ARPPU", value: `${summary.arppu_stars} ⭐`, note: `${summary.unique_payers} платників`, icon: Users },
      { label: "Trial → paid", value: `${summary.trial_conversion_percent}%`, note: `${summary.trial_previews} preview · ${summary.trial_invoices} invoice · ${summary.trial_converted} paid`, icon: ArrowUpRight },
      { label: "Повернення", value: `${summary.refunded_stars} ⭐`, note: `${summary.refunds} операцій`, icon: ArrowDownRight },
      { label: "VIP завершується", value: summary.expiring_7d, note: "у наступні 7 днів", icon: CalendarClock },
    ];
  }, [days, summary]);

  return (
    <div className="owner-page owner-payments-page">
      <header className="owner-page-heading owner-payments-heading">
        <div>
          <p>Telegram Stars</p>
          <h2>Оплати та підписки</h2>
          <span>Фінансові дані, конверсія та контроль VIP в одному місці.</span>
        </div>
        <button type="button" onClick={() => void exportCsv()} disabled={busy === "export"}>
          {busy === "export" ? <RefreshCw className="spin" /> : <Download />}
          CSV
        </button>
      </header>

      <div className="owner-revenue-periods" aria-label="Період аналітики">
        {[7, 30, 90, 366].map((value) => (
          <button type="button" className={days === value ? "is-active" : ""} key={value} onClick={() => setDays(value)}>
            {value === 366 ? "Рік" : `${value} днів`}
          </button>
        ))}
      </div>

      {error ? <button className="owner-error-banner" type="button" onClick={() => setError("")}>{error}</button> : null}

      {loading && !summary ? (
        <div className="owner-loading-block"><RefreshCw className="spin" /> Збираємо фінансову аналітику…</div>
      ) : null}

      {summary ? (
        <>
          <section className="owner-revenue-metrics">
            {metrics.map(({ label, value, note, icon: Icon }) => (
              <article key={label}>
                <span><Icon size={17} /></span>
                <small>{label}</small>
                <strong>{typeof value === "number" ? value.toLocaleString("uk-UA") : value}</strong>
                <p>{note}</p>
              </article>
            ))}
          </section>

          <section className="owner-revenue-grid">
            <article className="owner-panel owner-revenue-chart">
              <div className="owner-section-title">
                <div><p>Revenue timeline</p><h3>Чисті Stars по днях</h3></div>
                <CircleDollarSign size={20} />
              </div>
              <div className="owner-stars-chart" aria-label="Графік доходу">
                {timeline.map((point) => (
                  <div key={point.date} title={`${formatShortDate(point.date)} · ${point.net_stars} Stars`}>
                    <span style={{ height: `${Math.max(5, (point.net_stars / maxNet) * 100)}%` }} />
                    {point.refunded_stars ? <i style={{ height: `${Math.max(3, (point.refunded_stars / maxNet) * 100)}%` }} /> : null}
                    <small>{new Date(point.date).getDate()}</small>
                  </div>
                ))}
              </div>
              <footer><span><b /> Чисті Stars</span><span><b className="is-refund" /> Повернення</span></footer>
            </article>

            <article className="owner-panel owner-plan-distribution">
              <div className="owner-section-title">
                <div><p>Product mix</p><h3>Тарифи</h3></div>
                <WalletCards size={20} />
              </div>
              <div className="owner-plan-bars">
                {plans.length ? plans.map((plan) => (
                  <div key={plan.product_code}>
                    <header><span>{planLabels[plan.product_code] ?? plan.product_code}</span><strong>{plan.stars} ⭐</strong></header>
                    <i><b style={{ width: `${(plan.stars / totalPlanStars) * 100}%` }} /></i>
                    <small>{plan.payments} оплат</small>
                  </div>
                )) : <p className="owner-empty-inline">Оплат за цей період ще немає.</p>}
              </div>
            </article>
          </section>

          <section className="owner-panel owner-transactions-panel">
            <div className="owner-section-title">
              <div><p>Transactions</p><h3>Усі платежі</h3></div>
              <span className="owner-status-dot">{total}</span>
            </div>
            <div className="owner-payment-filters">
              <label className="owner-payment-search"><Search size={16} /><input value={filters.q ?? ""} placeholder="Ім’я, username, ID або charge ID" onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))} /></label>
              <select value={filters.product ?? ""} onChange={(event) => setFilters((current) => ({ ...current, product: event.target.value || undefined }))}>
                <option value="">Усі тарифи</option>
                <option value="trial_7d">Trial</option>
                <option value="monthly_30d">30 днів</option>
                <option value="quarter_90d">90 днів</option>
                <option value="year_365d">365 днів</option>
              </select>
              <select value={filters.paymentStatus ?? ""} onChange={(event) => setFilters((current) => ({ ...current, paymentStatus: event.target.value || undefined }))}>
                <option value="">Усі статуси</option>
                <option value="paid">Оплачено</option>
                <option value="refunded">Повернено</option>
                <option value="refund_required">Потрібен refund</option>
              </select>
              <select value={filters.recurring ?? "all"} onChange={(event) => setFilters((current) => ({ ...current, recurring: event.target.value as RevenueFilters["recurring"] }))}>
                <option value="all">Усі типи</option>
                <option value="true">Підписки</option>
                <option value="false">Разові</option>
              </select>
            </div>

            <div className="owner-transaction-list">
              {transactions.map((payment) => (
                <button type="button" key={payment.id} onClick={() => void openTransaction(payment.id)}>
                  <span className={`owner-payment-status status-${payment.status}`}><Star size={14} /></span>
                  <div className="owner-payment-user"><strong>{payment.display_name}</strong><small>{payment.username ? `@${payment.username}` : `ID ${payment.telegram_user_id}`}</small></div>
                  <div><strong>{planLabels[payment.product_code] ?? payment.product_code}</strong><small>{payment.is_recurring ? "Автопідписка" : "Разова"}</small></div>
                  <div><strong>{payment.stars_amount} ⭐</strong><small>{formatDate(payment.paid_at)}</small></div>
                  <em className={`payment-pill status-${payment.status}`}>{statusLabel(payment.status)}</em>
                  {busy === `detail-${payment.id}` ? <RefreshCw className="spin" /> : <ChevronRight />}
                </button>
              ))}
              {!transactions.length && !loading ? <p className="owner-empty-inline">За цими фільтрами платежів немає.</p> : null}
            </div>
          </section>
        </>
      ) : null}

      {selected ? (
        <PaymentDrawer
          detail={selected}
          busy={busy}
          onClose={() => setSelected(null)}
          onUpdated={async () => {
            const detail = await revenueApi.detail(selected.id);
            setSelected(detail);
            await load();
          }}
          onBusy={setBusy}
          onError={setError}
        />
      ) : null}
    </div>
  );
}

interface DrawerProps {
  detail: RevenueTransactionDetail;
  busy: string;
  onClose(): void;
  onUpdated(): Promise<void>;
  onBusy(value: string): void;
  onError(value: string): void;
}

function PaymentDrawer({ detail, busy, onClose, onUpdated, onBusy, onError }: DrawerProps) {
  const [note, setNote] = useState(detail.note?.text ?? "");
  const [refundReason, setRefundReason] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [subscriptionReason, setSubscriptionReason] = useState("");

  const saveNote = async () => {
    onBusy("note");
    try {
      await revenueApi.note(detail.id, detail.telegram_user_id, note);
      await onUpdated();
      notify("success");
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "Не вдалося зберегти примітку.");
    } finally {
      onBusy("");
    }
  };

  const refund = async () => {
    onBusy("refund");
    try {
      await revenueApi.refund(detail.id, refundReason, confirmation);
      await onUpdated();
      notify("success");
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "Не вдалося повернути Stars.");
    } finally {
      onBusy("");
    }
  };

  const changeSubscription = async (canceled: boolean) => {
    onBusy("subscription");
    try {
      await revenueApi.subscription(detail.telegram_user_id, canceled, subscriptionReason);
      await onUpdated();
      notify("success");
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "Не вдалося змінити підписку.");
    } finally {
      onBusy("");
    }
  };

  return (
    <div className="owner-payment-drawer-backdrop" role="presentation" onClick={onClose}>
      <aside className="owner-payment-drawer" role="dialog" aria-modal="true" aria-label="Деталі платежу" onClick={(event) => event.stopPropagation()}>
        <header><div><p>TRANSACTION #{detail.id}</p><h2>{detail.display_name}</h2><span>{detail.username ? `@${detail.username}` : `Telegram ID ${detail.telegram_user_id}`}</span></div><button type="button" aria-label="Закрити" onClick={onClose}><X /></button></header>
        <section className="owner-payment-detail-grid">
          <div><small>Тариф</small><strong>{planLabels[detail.product_code] ?? detail.product_code}</strong></div>
          <div><small>Сума</small><strong>{detail.stars_amount} ⭐</strong></div>
          <div><small>Статус</small><strong>{statusLabel(detail.status)}</strong></div>
          <div><small>Оплачено</small><strong>{formatDate(detail.paid_at)}</strong></div>
          <div><small>VIP до</small><strong>{detail.granted_until ? formatDate(detail.granted_until) : "—"}</strong></div>
          <div><small>Тип</small><strong>{detail.is_recurring ? "Автопідписка" : "Разова"}</strong></div>
        </section>
        <section className="owner-drawer-section"><h3>Charge ID</h3><code>{detail.telegram_payment_charge_id}</code></section>
        <section className="owner-drawer-section"><h3>Приватна примітка</h3><textarea value={note} maxLength={1000} placeholder="Внутрішня примітка для власника" onChange={(event) => setNote(event.target.value)} /><button type="button" disabled={!note.trim() || busy === "note"} onClick={() => void saveNote()}>{busy === "note" ? <RefreshCw className="spin" /> : null} Зберегти примітку</button></section>
        {detail.is_recurring && detail.status === "paid" ? (
          <section className="owner-drawer-section"><h3>Автопродовження</h3><input value={subscriptionReason} placeholder="Причина зміни" onChange={(event) => setSubscriptionReason(event.target.value)} /><div className="owner-drawer-actions"><button type="button" disabled={subscriptionReason.trim().length < 3 || busy === "subscription"} onClick={() => void changeSubscription(true)}>Вимкнути</button><button type="button" disabled={subscriptionReason.trim().length < 3 || busy === "subscription"} onClick={() => void changeSubscription(false)}>Відновити</button></div></section>
        ) : null}
        <section className="owner-drawer-section owner-drawer-section--danger"><h3>Повернення Stars</h3>{detail.refund.eligible ? <><p>Дозволено лише для останньої активної покупки. Інші покупки або подарований VIP не змінюються.</p><input value={refundReason} placeholder="Причина повернення" onChange={(event) => setRefundReason(event.target.value)} /><input value={confirmation} placeholder={`ПОВЕРНУТИ ${detail.stars_amount} STARS`} onChange={(event) => setConfirmation(event.target.value)} /><button type="button" disabled={refundReason.trim().length < 5 || confirmation !== `ПОВЕРНУТИ ${detail.stars_amount} STARS` || busy === "refund"} onClick={() => void refund()}>{busy === "refund" ? <RefreshCw className="spin" /> : <RotateCcw />} Повернути {detail.stars_amount} ⭐</button></> : <p>{detail.refund.reason || "Повернення для цієї операції недоступне."}</p>}</section>
        <section className="owner-drawer-section"><h3>Історія користувача</h3><div className="owner-payment-history">{detail.history.map((item) => <div key={item.id}><span>{planLabels[item.product_code] ?? item.product_code}</span><strong>{item.stars_amount} ⭐</strong><small>{formatDate(item.paid_at)}</small></div>)}</div></section>
      </aside>
    </div>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
function formatShortDate(value: string): string {
  return new Intl.DateTimeFormat("uk-UA", { day: "2-digit", month: "short" }).format(new Date(value));
}
function statusLabel(value: string): string {
  return value === "paid" ? "Оплачено" : value === "refunded" ? "Повернено" : value === "refund_required" ? "Потрібен refund" : value;
}
