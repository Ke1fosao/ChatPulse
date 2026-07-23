import {
  ArrowLeft,
  BarChart3,
  ExternalLink,
  LayoutDashboard,
  RefreshCw,
  Settings2,
  Share2,
  Trophy,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, downloadBlob } from "../../api/client";
import type {
  GroupAnalyticsPayload,
  GroupAwardsPayload,
  GroupCenterTab,
  GroupOverviewPayload,
  GroupRankingPayload,
} from "../../api/groups-v2";
import { groupCacheKey, isGroupsV2Card } from "../../api/groups-v2";
import type { GroupCardData, GroupSettings, Metric, Period } from "../../api/types";
import { usePremium } from "../../premium/PremiumContext";
import { haptic, notify, openTelegramLink } from "../../telegram/sdk";
import { GroupSettingsPanel } from "../admin/GroupSettingsPanel";
import { GroupAnalyticsTab } from "./GroupAnalyticsTab";
import { GroupAwardsTab } from "./GroupAwardsTab";
import { GroupOverviewTab } from "./GroupOverviewTab";
import { GroupRankingTab } from "./GroupRankingTab";

interface GroupCenterPageProps {
  group: GroupCardData;
  onBack(): void;
}

type TabPayload =
  | GroupOverviewPayload
  | GroupRankingPayload
  | GroupAnalyticsPayload
  | GroupAwardsPayload;

const tabs: Array<{ id: GroupCenterTab; label: string; icon: typeof LayoutDashboard }> = [
  { id: "overview", label: "Огляд", icon: LayoutDashboard },
  { id: "ranking", label: "Рейтинг", icon: Trophy },
  { id: "analytics", label: "Аналітика", icon: BarChart3 },
  { id: "awards", label: "Нагороди", icon: Trophy },
];

const periods: Array<{ id: Period; label: string }> = [
  { id: "week", label: "7 днів" },
  { id: "month", label: "30 днів" },
  { id: "all", label: "Весь час" },
];

function GroupCenterSkeleton() {
  return (
    <div className="group-center-skeleton" aria-label="Завантаження розділу групи">
      <span />
      <span />
      <span />
    </div>
  );
}

async function shareBlob(blob: Blob, title: string, filename: string): Promise<void> {
  const shareNavigator = navigator as Navigator & {
    canShare?: (data: ShareData) => boolean;
    share?: (data: ShareData) => Promise<void>;
  };
  const file = new File([blob], filename, { type: blob.type || "image/png" });
  const shareData: ShareData = { title, files: [file] };
  if (shareNavigator.share && (!shareNavigator.canShare || shareNavigator.canShare(shareData))) {
    await shareNavigator.share(shareData);
    return;
  }
  downloadBlob(blob, filename);
}

export function GroupCenterPage({ group, onBack }: GroupCenterPageProps) {
  const premium = usePremium();
  const cache = useRef(new Map<string, TabPayload>());
  const [tab, setTab] = useState<GroupCenterTab>("overview");
  const [period, setPeriod] = useState<Period>("week");
  const [metric, setMetric] = useState<Metric>("xp");
  const [overview, setOverview] = useState<GroupOverviewPayload | null>(null);
  const [ranking, setRanking] = useState<GroupRankingPayload | null>(null);
  const [analytics, setAnalytics] = useState<GroupAnalyticsPayload | null>(null);
  const [awards, setAwards] = useState<GroupAwardsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [refreshNotice, setRefreshNotice] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [actionBusy, setActionBusy] = useState<string | null>(null);

  const applyPayload = useCallback((targetTab: GroupCenterTab, payload: TabPayload) => {
    if (targetTab === "overview") setOverview(payload as GroupOverviewPayload);
    if (targetTab === "ranking") setRanking(payload as GroupRankingPayload);
    if (targetTab === "analytics") setAnalytics(payload as GroupAnalyticsPayload);
    if (targetTab === "awards") setAwards(payload as GroupAwardsPayload);
  }, []);

  const fetchPayload = useCallback(
    (targetTab: GroupCenterTab): Promise<TabPayload> => {
      if (targetTab === "overview") return api.groupOverview(group.telegram_chat_id, period);
      if (targetTab === "ranking") {
        return api.groupRanking(group.telegram_chat_id, metric, period);
      }
      if (targetTab === "analytics") return api.groupAnalytics(group.telegram_chat_id, period);
      return api.groupAwards(group.telegram_chat_id, period);
    },
    [group.telegram_chat_id, metric, period],
  );

  const loadTab = useCallback(
    async (targetTab: GroupCenterTab, force = false) => {
      const key = groupCacheKey(group.telegram_chat_id, targetTab, period, metric);
      const cached = cache.current.get(key);
      if (cached && !force) {
        applyPayload(targetTab, cached);
        setLoading(false);
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError("");
      setRefreshNotice("");
      try {
        const payload = await fetchPayload(targetTab);
        cache.current.set(key, payload);
        applyPayload(targetTab, payload);
      } catch (reason) {
        const message = reason instanceof Error ? reason.message : "Не вдалося завантажити розділ.";
        if (cached) setRefreshNotice("Дані показано з кешу. Не вдалося оновити їх зараз.");
        else setError(message);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [applyPayload, fetchPayload, group.telegram_chat_id, metric, period],
  );

  useEffect(() => {
    void loadTab(tab);
  }, [loadTab, tab]);

  useEffect(() => {
    cache.current.clear();
    setOverview(null);
    setRanking(null);
    setAnalytics(null);
    setAwards(null);
    setTab("overview");
    setPeriod("week");
    setMetric("xp");
  }, [group.telegram_chat_id]);

  const currentPayload = useMemo(() => {
    if (tab === "overview") return overview;
    if (tab === "ranking") return ranking;
    if (tab === "analytics") return analytics;
    return awards;
  }, [analytics, awards, overview, ranking, tab]);

  const serverGroup = overview?.group;
  const initialStatus = isGroupsV2Card(group)
    ? group.status
    : group.period.messages_count > 0
      ? { id: "active", label: "Активна", tone: "success" as const }
      : { id: "quiet", label: "Тиха", tone: "neutral" as const };
  const status = serverGroup?.status ?? initialStatus;
  const isAdmin = overview?.capabilities?.is_admin ?? group.is_admin;
  const telegramUrl = serverGroup?.telegram_url ?? null;

  const switchTab = (nextTab: GroupCenterTab) => {
    haptic("light");
    setTab(nextTab);
  };

  const updateOverviewSettings = (settings: GroupSettings) => {
    setOverview((current) => (current ? { ...current, settings } : current));
    setAnalytics((current) => (current ? { ...current, settings } : current));
    for (const [key, value] of cache.current.entries()) {
      if (key.startsWith(`${group.telegram_chat_id}:overview:`)) {
        cache.current.set(key, { ...(value as GroupOverviewPayload), settings });
      }
      if (key.startsWith(`${group.telegram_chat_id}:analytics:`)) {
        cache.current.set(key, { ...(value as GroupAnalyticsPayload), settings });
      }
    }
  };

  const saveSettings = async (settings: Partial<GroupSettings>) => {
    const updated = await api.updateSettings(group.telegram_chat_id, settings);
    updateOverviewSettings(updated);
    return updated;
  };

  const resetGroup = async () => {
    await api.resetGroup(group.telegram_chat_id);
    cache.current.clear();
    setSettingsOpen(false);
    await loadTab("overview", true);
  };

  const shareSummary = async () => {
    setActionBusy("share");
    try {
      const blob = await api.weeklyCard(group.telegram_chat_id);
      await shareBlob(blob, `ChatPulse · ${group.title}`, `chatpulse-${group.telegram_chat_id}.png`);
      notify("success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося поділитися звітом.");
      notify("error");
    } finally {
      setActionBusy(null);
    }
  };

  const sendReport = async () => {
    setActionBusy("report");
    try {
      await api.sendGroupReport(group.telegram_chat_id);
      notify("success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося надіслати звіт.");
      notify("error");
    } finally {
      setActionBusy(null);
    }
  };

  const togglePaused = async () => {
    if (!overview) return;
    const nextPaused = !overview.settings.is_paused;
    const confirmed = window.confirm(
      nextPaused
        ? "Призупинити збір аналітики для цієї групи?"
        : "Відновити збір аналітики для цієї групи?",
    );
    if (!confirmed) return;
    setActionBusy("pause");
    try {
      if (nextPaused) await api.pauseGroupAnalytics(group.telegram_chat_id);
      else await api.resumeGroupAnalytics(group.telegram_chat_id);
      updateOverviewSettings({ ...overview.settings, is_paused: nextPaused });
      notify("success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося змінити стан аналітики.");
      notify("error");
    } finally {
      setActionBusy(null);
    }
  };

  if (settingsOpen && overview && isAdmin) {
    return (
      <div className="page group-center group-center--settings">
        <GroupSettingsPanel
          chatId={group.telegram_chat_id}
          settings={overview.settings}
          onSave={saveSettings}
          onReset={resetGroup}
          onBack={() => setSettingsOpen(false)}
        />
      </div>
    );
  }

  return (
    <div className="page group-center">
      <header className="group-center-header">
        <button className="icon-button" type="button" onClick={onBack} aria-label="Назад до груп">
          <ArrowLeft size={20} />
        </button>
        <span className="group-center-avatar">{group.initials}</span>
        <div className="group-center-header__copy">
          <p className="eyebrow">Центр групи</p>
          <h2>{group.title}</h2>
          <span className={`group-status group-status--${status.tone}`}><i /> {status.label}</span>
        </div>
        <div className="group-center-header__actions">
          {telegramUrl ? (
            <button type="button" onClick={() => openTelegramLink(telegramUrl)} aria-label="Відкрити в Telegram">
              <ExternalLink size={18} />
            </button>
          ) : null}
          <button type="button" disabled={actionBusy === "share"} onClick={() => void shareSummary()} aria-label="Поділитися статистикою">
            {actionBusy === "share" ? <RefreshCw className="spin" size={18} /> : <Share2 size={18} />}
          </button>
          {isAdmin && overview ? (
            <button type="button" onClick={() => setSettingsOpen(true)} aria-label="Налаштування групи">
              <Settings2 size={18} />
            </button>
          ) : null}
        </div>
      </header>

      <nav className="group-center-tabs" aria-label="Розділи групи">
        {tabs.map((item) => {
          const Icon = item.icon;
          return (
            <button
              className={tab === item.id ? "is-active" : ""}
              key={item.id}
              type="button"
              onClick={() => switchTab(item.id)}
            >
              <Icon size={16} /> {item.label}
            </button>
          );
        })}
      </nav>

      <div className="group-center-controls">
        <div className="segmented-control group-period-control" aria-label="Період статистики">
          {periods.map((item) => (
            <button
              className={period === item.id ? "is-active" : ""}
              key={item.id}
              type="button"
              onClick={() => setPeriod(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        {refreshing ? <span className="group-refreshing"><RefreshCw className="spin" size={13} /> Оновлення</span> : null}
      </div>

      {refreshNotice ? <button className="group-cache-notice" type="button" onClick={() => void loadTab(tab, true)}>{refreshNotice} Натисни, щоб повторити.</button> : null}
      {error ? (
        <section className="group-tab-error">
          <strong>Не вдалося завантажити розділ</strong>
          <span>{error}</span>
          <button type="button" onClick={() => void loadTab(tab, true)}><RefreshCw size={16} /> Повторити</button>
        </section>
      ) : null}

      {loading && !currentPayload ? <GroupCenterSkeleton /> : null}

      {tab === "overview" && overview ? (
        <GroupOverviewTab
          data={overview}
          actionBusy={actionBusy}
          onOpenRanking={() => switchTab("ranking")}
          onShare={() => void shareSummary()}
          onSendReport={() => void sendReport()}
          onTogglePaused={() => void togglePaused()}
        />
      ) : null}
      {tab === "ranking" && ranking ? (
        <GroupRankingTab data={ranking} metric={metric} onMetricChange={setMetric} />
      ) : null}
      {tab === "analytics" && analytics ? (
        <GroupAnalyticsTab
          data={analytics}
          account={premium.account}
          trialAvailable={premium.trialAvailable}
          onOpenVip={premium.openVip}
        />
      ) : null}
      {tab === "awards" && awards ? <GroupAwardsTab data={awards} /> : null}
    </div>
  );
}
