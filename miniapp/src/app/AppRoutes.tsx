import { AlertTriangle, RefreshCw } from "lucide-react";
import { Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import type { GroupsV2CardData } from "../api/groups-v2";
import type { Achievement, GroupCardData, HomePayload } from "../api/types";
import { AchievementsPage } from "../features/achievements/AchievementsPage";
import { GroupCenterPage } from "../features/groups/GroupCenterPage";
import { GroupsPage } from "../features/groups/GroupsPage";
import { HomePage } from "../features/home/HomePage";
import { ProfilePage } from "../features/profile/ProfilePage";
import { appPaths } from "../routing/paths";

interface AppRoutesProps {
  home: HomePayload;
  groups: GroupsV2CardData[];
  achievements: Achievement[];
  achievementLoading: boolean;
  achievementsError: string;
  groupsLoading: boolean;
  groupsError: string;
  onToggleFavorite(group: GroupsV2CardData, nextValue: boolean): Promise<void>;
  onReload(): void;
  onRefreshAchievements(): void;
  onShare(): void;
  onOpenLevels(): void;
}

export function AppRoutes(props: AppRoutesProps) {
  const navigate = useNavigate();
  const openGroup = (group: GroupCardData) => navigate(appPaths.group(group.telegram_chat_id));

  return (
    <Routes>
      <Route
        index
        element={
          <HomePage
            data={props.home}
            onOpenGroup={openGroup}
            onOpenAchievements={() => navigate(appPaths.achievements)}
            onOpenLevels={props.onOpenLevels}
            onShareProfile={props.onShare}
          />
        }
      />
      <Route
        path="groups"
        element={
          props.groupsError && props.groups.length === 0 ? (
            <ResourceError
              title="Не вдалося завантажити групи"
              message={props.groupsError}
              onRetry={props.onReload}
            />
          ) : (
            <GroupsPage
              groups={props.groups}
              loading={props.groupsLoading}
              error={props.groupsError}
              onOpenGroup={openGroup}
              onToggleFavorite={props.onToggleFavorite}
              onRefresh={props.onReload}
            />
          )
        }
      />
      <Route path="groups/:telegramChatId" element={<GroupCenterPageRoute groups={props.groups} />} />
      <Route
        path="achievements"
        element={
          props.achievementsError && props.achievements.length === 0 ? (
            <ResourceError
              title="Не вдалося завантажити досягнення"
              message={props.achievementsError}
              onRetry={props.onRefreshAchievements}
            />
          ) : (
            <AchievementsPage
              achievements={props.achievements}
              loading={props.achievementLoading}
              error={props.achievementsError}
              onRefresh={props.onRefreshAchievements}
            />
          )
        }
      />
      <Route
        path="profile"
        element={
          <ProfilePage
            data={props.home}
            onShare={props.onShare}
            onOpenLevels={props.onOpenLevels}
            onOpenAchievements={() => navigate(appPaths.achievements)}
            onOpenGroups={() => navigate(appPaths.groups)}
          />
        }
      />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  );
}

function ResourceError({
  title,
  message,
  onRetry,
}: {
  title: string;
  message: string;
  onRetry(): void;
}) {
  return (
    <main className="standalone-screen standalone-screen--inline">
      <span className="standalone-screen__error"><AlertTriangle size={30} /></span>
      <h2>{title}</h2>
      <p>{message}</p>
      <button className="primary-button" type="button" onClick={onRetry}>
        <RefreshCw size={18} /> Повторити
      </button>
    </main>
  );
}


function GroupCenterPageRoute({ groups }: { groups: GroupsV2CardData[] }) {
  const navigate = useNavigate();
  const { telegramChatId } = useParams<{ telegramChatId: string }>();
  const chatId = Number(telegramChatId);
  const group = groups.find((item) => item.telegram_chat_id === chatId);
  return group ? (
    <GroupCenterPage group={group} onBack={() => navigate(appPaths.groups)} />
  ) : (
    <Navigate to="../groups" replace />
  );
}
