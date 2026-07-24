import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { GroupsV2CardData } from "../../api/groups-v2";
import type { Achievement, HomePayload } from "../../api/types";
import { initTelegram, notify } from "../../telegram/sdk";

export function useAppBootstrap() {
  const [home, setHome] = useState<HomePayload | null>(null);
  const [groups, setGroups] = useState<GroupsV2CardData[]>([]);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [blockedAccount, setBlockedAccount] = useState<{ reason: string | null } | null>(null);

  const reload = useCallback(async () => {
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
        setError(reason instanceof ApiError ? reason.message : "Не вдалося відкрити ChatPulse.");
        notify("error");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    initTelegram();
    void reload();
  }, [reload]);

  return {
    home,
    groups,
    achievements,
    loading,
    error,
    blockedAccount,
    setGroups,
    setAchievements,
    setError,
    reload,
  };
}
