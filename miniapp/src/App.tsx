import { AlertTriangle, RefreshCw, Sparkles } from "lucide-react";
import { useState } from "react";
import {
  MemoryRouter,
  useInRouterContext,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { AppRoutes } from "./app/AppRoutes";
import { useAchievements } from "./app/hooks/useAchievements";
import { useAppBootstrap } from "./app/hooks/useAppBootstrap";
import { useGroups } from "./app/hooks/useGroups";
import type { TabId } from "./api/types";
import { AppShell } from "./components/AppShell";
import { LevelsDialog } from "./components/LevelsDialog";
import { ShareCardDialog } from "./components/ShareCardDialog";
import { BlockedAccountPage } from "./features/access/BlockedAccountPage";
import { AchievementCelebrationLayer } from "./features/achievements/AchievementCelebration";
import { appPaths } from "./routing/paths";
import { isTelegramContext } from "./telegram/sdk";
import "./styles/app";

function tabFromPath(pathname: string): TabId {
  if (pathname.startsWith(appPaths.groups)) return "groups";
  if (pathname.startsWith(appPaths.achievements)) return "achievements";
  if (pathname.startsWith(appPaths.profile)) return "profile";
  return "home";
}

export function App() {
  const isInsideRouter = useInRouterContext();

  if (!isInsideRouter) {
    return (
      <MemoryRouter initialEntries={[appPaths.home]}>
        <AppContent />
      </MemoryRouter>
    );
  }

  return <AppContent />;
}

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const [shareOpen, setShareOpen] = useState(false);
  const [levelsOpen, setLevelsOpen] = useState(false);
  const bootstrap = useAppBootstrap();
  const groups = useGroups(bootstrap.setGroups, bootstrap.setError);
  const achievements = useAchievements(bootstrap.setAchievements);

  if (!isTelegramContext()) {
    return (
      <main className="standalone-screen">
        <span><Sparkles size={32} /></span>
        <h1>Відкрий ChatPulse через Telegram</h1>
        <p>Mini App авторизується без паролів — напряму через твій Telegram-профіль.</p>
      </main>
    );
  }

  if (bootstrap.loading) {
    return (
      <main className="boot-screen">
        <span className="boot-logo"><Sparkles /></span>
        <h1>ChatPulse</h1>
        <p>Збираємо твій пульс…</p>
        <div className="boot-progress"><span /></div>
      </main>
    );
  }

  if (bootstrap.blockedAccount) {
    return <BlockedAccountPage reason={bootstrap.blockedAccount.reason} />;
  }

  if (!bootstrap.home) {
    return (
      <main className="standalone-screen">
        <span className="standalone-screen__error"><AlertTriangle size={30} /></span>
        <h1>Не вдалося відкрити профіль</h1>
        <p>{bootstrap.error || "Спробуй оновити Mini App."}</p>
        <button className="primary-button" type="button" onClick={() => void bootstrap.reload()}>
          <RefreshCw size={18} /> Повторити
        </button>
      </main>
    );
  }

  return (
    <>
      <AppShell
        activeTab={tabFromPath(location.pathname)}
        onTabChange={(tab) => navigate(tab === "home" ? appPaths.home : appPaths[tab])}
        badge={achievements.loading ? "SYNC" : "LIVE"}
      >
        {bootstrap.error ? (
          <button className="error-banner" type="button" onClick={() => bootstrap.setError("")}>
            <AlertTriangle size={17} /> {bootstrap.error}
          </button>
        ) : null}
        <AppRoutes
          home={bootstrap.home}
          groups={bootstrap.groups}
          achievements={bootstrap.achievements}
          achievementLoading={achievements.loading}
          onToggleFavorite={groups.toggleFavorite}
          onReload={() => void bootstrap.reload()}
          onRefreshAchievements={() => void achievements.refresh()}
          onShare={() => setShareOpen(true)}
          onOpenLevels={() => setLevelsOpen(true)}
        />
      </AppShell>
      <ShareCardDialog data={bootstrap.home} open={shareOpen} onClose={() => setShareOpen(false)} />
      <LevelsDialog open={levelsOpen} onClose={() => setLevelsOpen(false)} />
      <AchievementCelebrationLayer
        onOpenCollection={() => {
          navigate(appPaths.achievements);
          void achievements.refresh();
        }}
      />
    </>
  );
}
