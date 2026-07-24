import "./styles";
import {
  Check,
  ChevronLeft,
  Clock3,
  Crown,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Star,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { VipConfirmSheet } from "../premium/VipConfirmSheet";
import {
  bindBackButton,
  initTelegram,
  isTelegramContext,
  notify,
  openInvoice,
} from "../telegram/sdk";
import type { VipPayment, VipPlansPayload, VipPlan } from "./types";
import { vipApi, VipApiError } from "./vipApi";

const productLabels: Record<string, string> = {
  trial_7d: "Пробний VIP · 7 днів",
  monthly_30d: "VIP · 30 днів",
  quarter_90d: "VIP · 90 днів",
  year_365d: "VIP · 365 днів",
};

export function VipApp() {
  const [data, setData] = useState<VipPlansPayload | null>(null);
  const [payments, setPayments] = useState<VipPayment[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<VipPlan | null>(null);
  const [successPlan, setSuccessPlan] = useState<VipPlan | null>(null);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const source = new URLSearchParams(window.location.search).get("source");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [plansPayload, history] = await Promise.all([vipApi.plans(), vipApi.history()]);
      setData(plansPayload);
      setPayments(history);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося відкрити VIP.");
      notify("error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    initTelegram();
    void load();
    return bindBackButton(() => window.location.assign("/miniapp"));
  }, [load]);

  const confirmBuy = async (plan: VipPlan) => {
    setBusy(plan.code);
    setError("");
    setMessage("");
    try {
      const invoice = await vipApi.invoice(plan.code);
      const invoiceStatus = await openInvoice(invoice.invoice_url);
      if (invoiceStatus === "paid") {
        notify("success");
        setSelectedPlan(null);
        setSuccessPlan(plan);
        await delay(450);
        await load();
      } else if (invoiceStatus === "cancelled") {
        setSelectedPlan(null);
        setMessage("Оплату скасовано. Зірочки не списані.");
      } else if (invoiceStatus === "failed") {
        throw new Error("Telegram не зміг завершити оплату.");
      } else {
        setSelectedPlan(null);
        setMessage("Рахунок відкрито. Статус оновиться після підтвердження Telegram.");
      }
    } catch (reason) {
      setError(reason instanceof VipApiError ? reason.message : "Не вдалося створити рахунок.");
      notify("error");
    } finally {
      setBusy("");
    }
  };

  const changeSubscription = async (canceled: boolean) => {
    setBusy("subscription");
    setError("");
    try {
      await vipApi.subscription(canceled);
      setMessage(canceled ? "Автопродовження вимкнено." : "Автопродовження відновлено.");
      notify("success");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося змінити підписку.");
    } finally {
      setBusy("");
    }
  };

  const returnToFeatures = () => {
    if (source && window.history.length > 1) {
      window.history.back();
      return;
    }
    window.location.assign("/miniapp");
  };

  if (!isTelegramContext()) {
    return (
      <main className="vip-standalone">
        <Crown size={38} />
        <h1>Відкрий ChatPulse VIP через Telegram</h1>
        <p>Оплата Stars та VIP-статус привʼязані до перевіреного Telegram-профілю.</p>
      </main>
    );
  }

  if (loading && !data) {
    return (
      <main className="vip-standalone">
        <Sparkles size={38} />
        <h1>ChatPulse VIP</h1>
        <p>Завантажуємо тарифи…</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="vip-standalone">
        <XCircle size={38} />
        <h1>VIP тимчасово недоступний</h1>
        <p>{error}</p>
        <button type="button" onClick={() => void load()}><RefreshCw /> Повторити</button>
      </main>
    );
  }

  const premium = data.account.is_owner || data.account.is_vip;
  const subscription = data.billing.active_subscription;

  return (
    <main className="vip-page">
      <header className="vip-header">
        <button type="button" aria-label="Назад" onClick={() => window.location.assign("/miniapp")}><ChevronLeft /></button>
        <div><span>CHATPULSE</span><strong>VIP</strong></div>
        <Crown />
      </header>

      <section className={`vip-hero ${premium ? "vip-hero--active" : ""}`}>
        <div className="vip-hero__icon"><Crown /></div>
        <p>{premium ? "PREMIUM АКТИВНИЙ" : "ВІДКРИЙ БІЛЬШЕ"}</p>
        <h1>{data.account.is_owner ? "Owner-доступ" : premium ? "ChatPulse VIP" : "Спробуй VIP за 1 ⭐"}</h1>
        <span>
          {data.account.is_owner
            ? "Усі можливості активні назавжди"
            : data.billing.vip_expires_at
              ? `Діє до ${formatDate(data.billing.vip_expires_at)}`
              : "VIP-функції відкриваються прямо у відповідних розділах"}
        </span>
      </section>

      {successPlan ? (
        <section className="vip-success-card" role="status">
          <span><Crown size={28} /></span>
          <p>VIP активовано</p>
          <h2>{successPlan.title}</h2>
          <small>{data.billing.vip_expires_at ? `Діє до ${formatDate(data.billing.vip_expires_at)}` : "Статус оновлено"}</small>
          <button type="button" onClick={returnToFeatures}>Переглянути VIP-можливості</button>
        </section>
      ) : null}

      {message ? <button className="vip-message" type="button" onClick={() => setMessage("")}><Check /> {message}</button> : null}
      {error ? <button className="vip-error" type="button" onClick={() => setError("")}><XCircle /> {error}</button> : null}

      <section className="vip-section">
        <div className="vip-section__heading"><div><p>ТАРИФИ</p><h2>Обери свій VIP</h2></div><Star /></div>
        <div className="vip-plan-grid">
          {data.plans.map((plan) => (
            <article key={plan.code} className={`vip-plan vip-plan--${plan.code} ${!plan.available ? "is-disabled" : ""}`}>
              {plan.badge ? <em>{plan.badge}</em> : null}
              <h3>{plan.short_title}</h3>
              <div className="vip-plan__price"><strong>{plan.stars}</strong><span>⭐</span></div>
              <p>{plan.description}</p>
              <button type="button" disabled={!plan.available || Boolean(busy)} onClick={() => setSelectedPlan(plan)}>
                <Crown />
                {!plan.available ? "Недоступно" : plan.code === "trial_7d" ? "Спробувати" : "Придбати"}
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="vip-section vip-benefits">
        <div className="vip-section__heading"><div><p>МОЖЛИВОСТІ</p><h2>Free та VIP</h2></div><ShieldCheck /></div>
        <div className="vip-benefit-list">
          {data.benefits.map((benefit) => <div key={benefit}><Check /><span>{benefit}</span></div>)}
          <div><Check /><span>Жодних бонусів до XP — рейтинг залишається чесним</span></div>
        </div>
      </section>

      {subscription ? (
        <section className="vip-section vip-subscription">
          <div className="vip-section__heading"><div><p>ПІДПИСКА</p><h2>Автопродовження</h2></div><Clock3 /></div>
          <p>Поточний період діє до <strong>{formatDate(subscription.expires_at)}</strong>.</p>
          <button type="button" disabled={busy === "subscription"} onClick={() => void changeSubscription(!subscription.is_canceled)}>
            {subscription.is_canceled ? "Відновити автопродовження" : "Вимкнути автопродовження"}
          </button>
        </section>
      ) : null}

      <section className="vip-section vip-history">
        <div className="vip-section__heading"><div><p>ІСТОРІЯ</p><h2>Платежі Stars</h2></div><Clock3 /></div>
        {payments.length ? payments.map((payment) => (
          <article key={payment.id}>
            <div><strong>{productLabels[payment.product_code] ?? payment.product_code}</strong><small>{formatDate(payment.paid_at)}</small></div>
            <span>{payment.stars_amount} ⭐</span>
            <em className={`status-${payment.status}`}>{payment.status === "paid" ? "Оплачено" : payment.status === "refunded" ? "Повернено" : payment.status}</em>
          </article>
        )) : <p className="vip-history__empty">Покупок ще не було.</p>}
      </section>

      <VipConfirmSheet plan={selectedPlan} busy={Boolean(busy)} onCancel={() => setSelectedPlan(null)} onConfirm={(plan) => void confirmBuy(plan)} />
    </main>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}
