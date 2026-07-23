import {
  Award,
  Check,
  ChevronLeft,
  Clock3,
  Crown,
  Download,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Star,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { Achievement, GroupCardData } from "../api/types";
import {
  bindBackButton,
  initTelegram,
  isTelegramContext,
  notify,
  openInvoice,
} from "../telegram/sdk";
import type { FeaturedAchievement, VipPayment, VipPlansPayload, VipPlan } from "./types";
import { saveBlob, vipApi, VipApiError } from "./vipApi";

const productLabels: Record<string, string> = {
  trial_7d: "Пробний VIP · 7 днів",
  monthly_30d: "VIP · 30 днів",
  quarter_90d: "VIP · 90 днів",
  year_365d: "VIP · 365 днів",
};

export function VipApp() {
  const [data, setData] = useState<VipPlansPayload | null>(null);
  const [payments, setPayments] = useState<VipPayment[]>([]);
  const [groups, setGroups] = useState<GroupCardData[]>([]);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [featured, setFeatured] = useState<FeaturedAchievement[]>([]);
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [plansPayload, history, groupItems, achievementItems, featuredItems] =
        await Promise.all([
          vipApi.plans(),
          vipApi.history(),
          api.groups(),
          vipApi.achievements(),
          vipApi.featured(),
        ]);
      setData(plansPayload);
      setPayments(history);
      setGroups(groupItems);
      setAchievements(achievementItems);
      setFeatured(featuredItems);
      setSelectedCodes(featuredItems.map((item) => item.code));
      setSelectedGroupId((current) => current ?? groupItems[0]?.telegram_chat_id ?? null);
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

  const earnedAchievements = useMemo(
    () => achievements.filter((item) => item.earned && !item.hidden).slice(0, 30),
    [achievements],
  );

  const buy = async (plan: VipPlan) => {
    setBusy(plan.code);
    setError("");
    setMessage("");
    try {
      const invoice = await vipApi.invoice(plan.code);
      const invoiceStatus = await openInvoice(invoice.invoice_url);
      if (invoiceStatus === "paid") {
        notify("success");
        setMessage("Оплату прийнято. Оновлюємо VIP-статус…");
        await delay(900);
        await load();
      } else if (invoiceStatus === "cancelled") {
        setMessage("Оплату скасовано. Зірочки не списані.");
      } else if (invoiceStatus === "failed") {
        throw new Error("Telegram не зміг завершити оплату.");
      } else {
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

  const exportAnalytics = async (format: "csv" | "pdf") => {
    if (selectedGroupId === null) return;
    setBusy(`export-${format}`);
    setError("");
    try {
      const blob = await vipApi.exportGroup(selectedGroupId, format);
      saveBlob(blob, `chatpulse-analytics.${format}`);
      notify("success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося створити експорт.");
    } finally {
      setBusy("");
    }
  };

  const toggleFeatured = (code: string) => {
    setSelectedCodes((current) => {
      if (current.includes(code)) return current.filter((item) => item !== code);
      if (current.length >= 3) {
        setMessage("Можна вибрати максимум три досягнення.");
        return current;
      }
      return [...current, code];
    });
  };

  const saveFeatured = async () => {
    setBusy("featured");
    setError("");
    try {
      const items = await vipApi.updateFeatured(selectedCodes);
      setFeatured(items);
      setMessage("Закріплені досягнення оновлено.");
      notify("success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося зберегти досягнення.");
    } finally {
      setBusy("");
    }
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
        <button type="button" aria-label="Назад" onClick={() => window.location.assign("/miniapp")}>
          <ChevronLeft />
        </button>
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
              : "Без переваг у XP — лише більше аналітики та оформлення"}
        </span>
      </section>

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
              <button
                type="button"
                disabled={!plan.available || Boolean(busy)}
                onClick={() => void buy(plan)}
              >
                {busy === plan.code ? <RefreshCw className="spin" /> : <Crown />}
                {!plan.available ? "Недоступно" : plan.code === "trial_7d" ? "Спробувати" : "Придбати"}
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="vip-section vip-benefits">
        <div className="vip-section__heading"><div><p>МОЖЛИВОСТІ</p><h2>Що входить</h2></div><ShieldCheck /></div>
        <div className="vip-benefit-list">
          {data.benefits.map((benefit) => <div key={benefit}><Check /><span>{benefit}</span></div>)}
        </div>
      </section>

      {subscription ? (
        <section className="vip-section vip-subscription">
          <div className="vip-section__heading"><div><p>ПІДПИСКА</p><h2>Автопродовження</h2></div><Clock3 /></div>
          <p>Поточний період діє до <strong>{formatDate(subscription.expires_at)}</strong>.</p>
          <button
            type="button"
            disabled={busy === "subscription"}
            onClick={() => void changeSubscription(!subscription.is_canceled)}
          >
            {subscription.is_canceled ? "Відновити автопродовження" : "Вимкнути автопродовження"}
          </button>
        </section>
      ) : null}

      <section className="vip-section vip-export">
        <div className="vip-section__heading"><div><p>ЕКСПОРТ</p><h2>Завантажити аналітику</h2></div><Download /></div>
        <select value={selectedGroupId ?? ""} onChange={(event) => setSelectedGroupId(Number(event.target.value))}>
          {groups.map((group) => <option value={group.telegram_chat_id} key={group.telegram_chat_id}>{group.title}</option>)}
        </select>
        <div className="vip-export__buttons">
          <button type="button" disabled={!premium || selectedGroupId === null || Boolean(busy)} onClick={() => void exportAnalytics("csv")}>CSV</button>
          <button type="button" disabled={!premium || selectedGroupId === null || Boolean(busy)} onClick={() => void exportAnalytics("pdf")}>PDF</button>
        </div>
        {!premium ? <small>Експорт відкривається після активації VIP.</small> : null}
      </section>

      <section className="vip-section vip-featured">
        <div className="vip-section__heading"><div><p>ПРОФІЛЬ</p><h2>Закріплені досягнення</h2></div><Award /></div>
        <p>Обери до трьох отриманих нагород. Зараз закріплено: {featured.length}/3.</p>
        <div className="vip-featured__list">
          {earnedAchievements.map((achievement) => {
            const selected = selectedCodes.includes(achievement.code);
            return (
              <button
                type="button"
                className={selected ? "is-selected" : ""}
                key={achievement.code}
                onClick={() => toggleFeatured(achievement.code)}
                disabled={!premium}
              >
                <span>{achievement.icon}</span><div><strong>{achievement.title}</strong><small>{achievement.description}</small></div>{selected ? <Check /> : null}
              </button>
            );
          })}
        </div>
        <button className="vip-featured__save" type="button" disabled={!premium || busy === "featured"} onClick={() => void saveFeatured()}>
          Зберегти вибір
        </button>
      </section>

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
    </main>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}
