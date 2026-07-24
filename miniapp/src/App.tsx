import { AlertTriangle, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "./api/client";
import type { GroupsV2CardData } from "./api/groups-v2";
import type { Achievement, HomePayload, TabId } from "./api/types";
import { AppShell } from "./components/AppShell";
import { LevelsDialog } from "./components/LevelsDialog";
import { ShareCardDialog } from "./components/ShareCardDialog";
import { BlockedAccountPage } from "./features/access/BlockedAccountPage";
import { AchievementCelebrationLayer } from "./features/achievements/AchievementCelebration";
import { AchievementsPage } from "./features/achievements/AchievementsPage";
import { GroupCenterPage } from "./features/groups/GroupCenterPage";
import { GroupsPage } from "./features/groups/GroupsPage";
import { HomePage } from "./features/home/HomePage";
import { ProfilePage } from "./features/profile/ProfilePage";
import { appPaths } from "./routing/paths";
import { bindBackButton, initTelegram, isTelegramContext, notify } from "./telegram/sdk";

interface GroupRouteProps {
  groups: GroupsV2CardData[];
}

function GroupRoute({ groups }: GroupRouteProps) {
  const navigate = useNavigate();
  const { telegramChatId } = useParams<{ telegramChatId: string }>();
  const selectedGroup = groups.find(
    (group) => String(group.telegram_chat_id) === telegramChatId,
  );

  useEffect(
    () => bindBackButton(() => navigate(appPaths.groups)),
    [navigate],
  );

  if (!selectedGroup) {
    return <Navigate to={appPaths.groups} replace />;
  }

  return (
    <GroupCenterPage
      group={selectedGroup}
      onBack={() => navigate(appPaths.groups)}
    />
  );
}

function tabFromPath(pathname: string): TabId {
  if (pathname.startsWith(appPaths.groups)) return "groups";
  if (pathname.startsWith(appPaths.achievements)) return "achievements";
  if (pathname.startsWith(appPaths.profile)) return "profile";
  return "home";
}

export function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [home, setHome] = useState<HomePayload | null>(null);
  const [groups, setGroups] = useState<GroupsV2CardData[]>([]);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [loading, setLoading] = useState(true);
  const [secondaryLoading, setSecondaryLoading] = useState(false);
  const [error, setError] = useState("");
  const [blockedAccount, setBlockedAccount] = useState<{ reason: string | null } | null>(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [levelsOpen, setLevelsOpen] = useState(false);

  const activeTab = useMemo(() => tabFromPath(location.pathname), [location.pathname]);

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
  }, []);

  useEffect(() => {
    initTelegram();
    void loadCore();
  }, [loadCore]);

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

  const openGroup = (telegramChatId: number) => navigate(appPaths.group(telegramChatId));

  return (
    <>
      <AppShell
        activeTab={activeTab}
        onTabChange={(tab) => {
          const destination = {
            home: appPaths.home,
            groups: appPaths.groups,
            achievements: appPaths.achievements,
            profile: appPaths.profile,
          }[tab];
          navigate(destination);
        }}
        badge={secondaryLoading ? "SYNC" : "LIVE"}
      >
        {error ? (
          <button className="error-banner" type="button" onClick={() => setError("")}>
            <AlertTriangle size={17} /> {error}
          </button>
        ) : null}

        <Routes>
          <Route
            index
            element={
              <HomePage
                data={home}
                onOpenGroup={(group) => openGroup(group.telegram_chat_id)}
                onOpenAchievements={() => navigate(appPaths.achievements)}
                onOpenLevels={() => setLevelsOpen(true)}
                onShareProfile={() => setShareOpen(true)}
              />
            }
          />
          <Route
            path="groups"
            element={
              <GroupsPage
                groups={groups}
                onOpenGroup={(group) => openGroup(group.telegram_chat_id)}
                onToggleFavorite={toggleFavorite}
                onRefresh={loadCore}
              />
            }
          />
          <Route path="groups/:telegramChatId" element={<GroupRoute groups={groups} />} />
          <Route
            path="achievements"
            element={
              <AchievementsPage
                achievements={achievements}
                loading={secondaryLoading}
                onRefresh={() => void refreshAchievements()}
              />
            }
          />
          <Route
            path="profile"
            element={
              <ProfilePage
                data={home}
                onShare={() => setShareOpen(true)}
                onOpenLevels={() => setLevelsOpen(true)}
                onOpenAchievements={() => navigate(appPaths.achievements)}
                onOpenGroups={() => navigate(appPaths.groups)}
              />
            }
          />
          <Route path="*" element={<Navigate to={appPaths.home} replace />} />
        </Routes>
      </AppShell>

      <ShareCardDialog data={home} open={shareOpen} onClose={() => setShareOpen(false)} />
      <LevelsDialog open={levelsOpen} onClose={() => setLevelsOpen(false)} />
      <AchievementCelebrationLayer
        onOpenCollection={() => {
          navigate(appPaths.achievements);
          void refreshAchievements();
        }}
      />
    </>
  );
}
