import { AlertTriangle, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "./api/client";
import type { GroupsV2CardData } from "./api/groups-v2";
import type {
  Achievement,
  GroupCardData,
  HomePayload,
  Metric,
  Period,
  RankingPayload,
  TabId,
} from "./api/types";
import { AppShell } from "./components/AppShell";
import { LevelsDialog } from "./components/LevelsDialog";
import { ShareCardDialog } from "./components/ShareCardDialog";
import { AchievementCelebrationLayer } from "./features/achievements/AchievementCelebration";
import { AchievementsPage } from "./features/achievements/AchievementsPage";
import { BlockedAccountPage } from "./features/access/BlockedAccountPage";
import { GroupCenterPage } from "./features/groups/GroupCenterPage";
import { GroupsPage } from "./features/groups/GroupsPage";
import { HomePage } from "./features/home/HomePage";
import { ProfilePage } from "./features/profile/ProfilePage";
import { RankingsPage } from "./features/rankings/RankingsPage";
import {
  bindBackButton,
  initTelegram,
  isTelegramContext,
  notify,
} from "./telegram/sdk";

export function App() {
  const [activeTab, setActiveTab] = useState<TabId>("home");
  const [home, setHome] = useState<HomePayload | null>(null);
  const [groups, setGroups] = useState<GroupsV2CardData[]>([]);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<GroupCardData | null>(null);
  const [ranking, setRanking] = useState<RankingPayload | null>(null);
  const [rankingGroupId, setRankingGroupId] = useState<number | null>(null);
  const [rankingMetric, setRankingMetric] = useState<Metric>("xp");
  const [rankingPeriod, setRankingPeriod] = useState<Period>("week");
  const [loading, setLoading] = useState(true);
  const [secondaryLoading, setSecondaryLoading] = useState(false);
  const [error, setError] = useState("");
  const [blockedAccount, setBlockedAccount] = useState<{ reason: string | null } | null>(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [levelsOpen, setLevelsOpen] = useState(false);

  const loadCore = useCallback(async () => {
    setLoading(true);
    setError("");
    setBlockedAccount(null);
    try {
      const [homePayload, groupPayload, achievementPayload] = await Promise.all([
        api.home(),
        api.groups(),
        api.achievements(),
      ]);
      setHome(homePayload);
      setGroups(groupPayload);
      setAchievements(achievementPayload);
      const initialGroupId = rankingGroupId ?? groupPayload[0]?.telegram_chat_id ?? null;
      setRankingGroupId(initialGroupId);
      notify("success");
    } catch (reason) {
      if (reason instanceof ApiError && reason.code === "ACCOUNT_BLOCKED") {
        setHome(null);
        setBlockedAccount({ reason: reason.reason ?? null });
      } else {
        const message =
          reason instanceof ApiError ? reason.message : "Не вдалося відкрити ChatPulse.";
        setError(message);
        notify("error");
      }
    } finally {
      setLoading(false);
    }
  }, [rankingGroupId]);

  useEffect(() => {
    initTelegram();
    void loadCore();
  }, [loadCore]);

  const loadRanking = useCallback(async () => {
    if (rankingGroupId === null) {
      setRanking(null);
      return;
    }
    setSecondaryLoading(true);
    try {
      setRanking(await api.rankings(rankingGroupId, rankingMetric, rankingPeriod));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося завантажити рейтинг.");
    } finally {
      setSecondaryLoading(false);
    }
  }, [rankingGroupId, rankingMetric, rankingPeriod]);

  useEffect(() => {
    if (activeTab === "rankings") void loadRanking();
  }, [activeTab, loadRanking]);

  useEffect(
    () => bindBackButton(selectedGroup ? () => setSelectedGroup(null) : null),
    [selectedGroup],
  );

  const openGroup = (group: GroupCardData) => {
    setSelectedGroup(group);
  };

  const toggleFavorite = useCallback(
    async (group: GroupsV2CardData, nextValue: boolean) => {
      setGroups((current) =>
        current.map((item) =>
          item.telegram_chat_id === group.telegram_chat_id
            ? { ...item, is_favorite: nextValue }
            : item,
        ),
      );
      try {
        await api.setGroupFavorite(group.telegram_chat_id, nextValue);
        notify("success");
      } catch (reason) {
        setGroups((current) =>
          current.map((item) =>
            item.telegram_chat_id === group.telegram_chat_id
              ? { ...item, is_favorite: !nextValue }
              : item,
          ),
        );
        setError(reason instanceof Error ? reason.message : "Не вдалося оновити обране.");
        notify("error");
        throw reason;
      }
    },
    [],
  );

  const refreshAchievements = async () => {
    setSecondaryLoading(true);
    try {
      setAchievements(await api.achievements());
    } finally {
      setSecondaryLoading(false);
    }
  };

  const renderedPage = useMemo(() => {
    if (!home) return null;
    if (selectedGroup) {
      return <GroupCenterPage group={selectedGroup} onBack={() => setSelectedGroup(null)} />;
    }
    if (activeTab === "groups") {
      return (
        <GroupsPage
          groups={groups}
          onOpenGroup={openGroup}
          onToggleFavorite={toggleFavorite}
          onRefresh={loadCore}
        />
      );
    }
    if (activeTab === "rankings") {
      return (
        <RankingsPage
          groups={groups}
          ranking={ranking}
          loading={secondaryLoading}
          selectedGroupId={rankingGroupId}
          metric={rankingMetric}
          period={rankingPeriod}
          onGroupChange={setRankingGroupId}
          onMetricChange={setRankingMetric}
          onPeriodChange={setRankingPeriod}
          onRefresh={() => void loadRanking()}
        />
      );
    }
    if (activeTab === "achievements") {
      return (
        <AchievementsPage
          achievements={achievements}
          loading={secondaryLoading}
          onRefresh={() => void refreshAchievements()}
        />
      );
    }
    if (activeTab === "profile") {
      return (
        <ProfilePage
          data={home}
          onShare={() => setShareOpen(true)}
          onOpenLevels={() => setLevelsOpen(true)}
          onOpenAchievements={() => setActiveTab("achievements")}
          onOpenGroups={() => setActiveTab("groups")}
        />
      );
    }
    return (
      <HomePage
        data={home}
        onOpenGroup={openGroup}
        onOpenAchievements={() => setActiveTab("achievements")}
        onOpenLevels={() => setLevelsOpen(true)}
        onShareProfile={() => setShareOpen(true)}
      />
    );
  }, [
    activeTab,
    achievements,
    groups,
    home,
    loadCore,
    loadRanking,
    ranking,
    rankingGroupId,
    rankingMetric,
    rankingPeriod,
    secondaryLoading,
    selectedGroup,
    toggleFavorite,
  ]);

  if (!isTelegramContext()) {
    return (
      <main className="standalone-screen">
        <span><Sparkles size={32} /></span>
        <h1>Відкрий ChatPulse через Telegram</h1>
        <p>Mini App авторизується без паролів — напряму через твій Telegram-профіль.</p>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="boot-screen">
        <span className="boot-logo"><Sparkles /></span>
        <h1>ChatPulse</h1>
        <p>Збираємо твій пульс…</p>
        <div className="boot-progress"><span /></div>
      </main>
    );
  }

  if (blockedAccount) {
    return <BlockedAccountPage reason={blockedAccount.reason} />;
  }

  if (!home) {
    return (
      <main className="standalone-screen">
        <span className="standalone-screen__error"><AlertTriangle size={30} /></span>
        <h1>Не вдалося відкрити профіль</h1>
        <p>{error || "Спробуй оновити Mini App."}</p>
        <button className="primary-button" type="button" onClick={() => void loadCore()}>
          <RefreshCw size={18} /> Повторити
        </button>
      </main>
    );
  }

  return (
    <>
      <AppShell
        activeTab={activeTab}
        onTabChange={(tab) => {
          setSelectedGroup(null);
          setActiveTab(tab);
        }}
        badge={secondaryLoading ? "SYNC" : "LIVE"}
      >
        {error ? (
          <button className="error-banner" type="button" onClick={() => setError("")}>
            <AlertTriangle size={17} /> {error}
          </button>
        ) : null}
        {renderedPage}
      </AppShell>
      <ShareCardDialog data={home} open={shareOpen} onClose={() => setShareOpen(false)} />
      <LevelsDialog open={levelsOpen} onClose={() => setLevelsOpen(false)} />
      <AchievementCelebrationLayer
        onOpenCollection={() => {
          setSelectedGroup(null);
          setActiveTab("achievements");
          void refreshAchievements();
        }}
      />
    </>
  );
}
