import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { GroupsV2CardData } from "../../api/groups-v2";
import type { Achievement, HomePayload, OnboardingPayload } from "../../api/types";
import { initTelegram, notify } from "../../telegram/sdk";
import { errorResource, idleResource, loadingResource, successResource } from "./resource";
import type { BootstrapResources, ResourceState } from "./types";

const completedOnboarding: OnboardingPayload = {
  completed_steps: 3,
  total_steps: 3,
  is_complete: true,
  primary_action: "done",
  add_group_url: null,
  linked_group: null,
  steps: [],
};

function message(reason: unknown, fallback: string): string {
  return reason instanceof ApiError || reason instanceof Error ? reason.message : fallback;
}

export function useBootstrapResources(): BootstrapResources {
  const [homeCore, setHomeCore] = useState<ResourceState<Omit<HomePayload, "onboarding">>>(
    idleResource(),
  );
  const [onboarding, setOnboarding] = useState<ResourceState<OnboardingPayload>>(idleResource());
  const [groups, setGroupsState] = useState<ResourceState<GroupsV2CardData[]>>(idleResource([]));
  const [achievements, setAchievementsState] = useState<ResourceState<Achievement[]>>(
    idleResource([]),
  );
  const [blockedAccount, setBlockedAccount] = useState<{ reason: string | null } | null>(null);
  const generation = useRef(0);
  const controllers = useRef(new Set<AbortController>());

  const begin = useCallback(() => {
    const controller = new AbortController();
    controllers.current.add(controller);
    return controller;
  }, []);

  const finish = useCallback((controller: AbortController) => {
    controllers.current.delete(controller);
  }, []);

  const isCurrent = useCallback((token: number, controller: AbortController) => (
    generation.current === token && !controller.signal.aborted
  ), []);

  const handleBlocked = useCallback((reason: unknown, token: number) => {
    if (!(reason instanceof ApiError) || reason.code !== "ACCOUNT_BLOCKED") return false;
    if (generation.current !== token) return true;
    controllers.current.forEach((controller) => controller.abort());
    controllers.current.clear();
    setBlockedAccount({ reason: reason.reason ?? null });
    setHomeCore(idleResource());
    return true;
  }, []);

  const loadHome = useCallback(async (token: number) => {
    const controller = begin();
    setHomeCore((current) => loadingResource(current));
    try {
      const data = await api.homeCore({ signal: controller.signal });
      if (isCurrent(token, controller)) setHomeCore(successResource(data));
    } catch (reason) {
      if (controller.signal.aborted || handleBlocked(reason, token)) return;
      if (isCurrent(token, controller)) {
        setHomeCore((current) => errorResource(current, message(reason, "Не вдалося відкрити ChatPulse.")));
        notify("error");
      }
    } finally {
      finish(controller);
    }
  }, [begin, finish, handleBlocked, isCurrent]);

  const loadOnboarding = useCallback(async (token: number) => {
    const controller = begin();
    setOnboarding((current) => loadingResource(current));
    try {
      const data = await api.onboarding({ signal: controller.signal });
      if (isCurrent(token, controller)) setOnboarding(successResource(data));
    } catch (reason) {
      if (controller.signal.aborted || handleBlocked(reason, token)) return;
      if (isCurrent(token, controller)) {
        setOnboarding((current) => errorResource(current, message(reason, "Не вдалося оновити старт.")));
      }
    } finally {
      finish(controller);
    }
  }, [begin, finish, handleBlocked, isCurrent]);

  const loadGroups = useCallback(async (token: number) => {
    const controller = begin();
    setGroupsState((current) => loadingResource(current));
    try {
      const data = await api.groups({ signal: controller.signal });
      if (isCurrent(token, controller)) setGroupsState(successResource(data));
    } catch (reason) {
      if (controller.signal.aborted || handleBlocked(reason, token)) return;
      if (isCurrent(token, controller)) {
        setGroupsState((current) => errorResource(current, message(reason, "Не вдалося завантажити групи.")));
      }
    } finally {
      finish(controller);
    }
  }, [begin, finish, handleBlocked, isCurrent]);

  const loadAchievements = useCallback(async (token: number) => {
    const controller = begin();
    setAchievementsState((current) => loadingResource(current));
    try {
      const data = await api.achievements(undefined, { signal: controller.signal });
      if (isCurrent(token, controller)) setAchievementsState(successResource(data));
    } catch (reason) {
      if (controller.signal.aborted || handleBlocked(reason, token)) return;
      if (isCurrent(token, controller)) {
        setAchievementsState((current) => errorResource(
          current,
          message(reason, "Не вдалося завантажити досягнення."),
        ));
      }
    } finally {
      finish(controller);
    }
  }, [begin, finish, handleBlocked, isCurrent]);

  const reloadCritical = useCallback(async () => {
    generation.current += 1;
    const token = generation.current;
    controllers.current.forEach((controller) => controller.abort());
    controllers.current.clear();
    setBlockedAccount(null);
    await Promise.allSettled([
      loadHome(token),
      loadOnboarding(token),
      loadGroups(token),
      loadAchievements(token),
    ]);
    if (generation.current === token && !blockedAccount) notify("success");
  }, [blockedAccount, loadAchievements, loadGroups, loadHome, loadOnboarding]);

  const retryGroups = useCallback(async () => loadGroups(generation.current), [loadGroups]);
  const retryAchievements = useCallback(
    async () => loadAchievements(generation.current),
    [loadAchievements],
  );
  const retryOnboarding = useCallback(
    async () => loadOnboarding(generation.current),
    [loadOnboarding],
  );

  useEffect(() => {
    initTelegram();
    void reloadCritical();
    return () => {
      generation.current += 1;
      controllers.current.forEach((controller) => controller.abort());
      controllers.current.clear();
    };
  }, []); // Telegram initialization and first generation run exactly once.

  const home = useMemo<ResourceState<HomePayload>>(() => {
    if (homeCore.data) {
      return {
        status: homeCore.status,
        data: {
          ...homeCore.data,
          onboarding: onboarding.data ?? completedOnboarding,
        },
        error: homeCore.error,
      };
    }
    return { status: homeCore.status, data: null, error: homeCore.error };
  }, [homeCore, onboarding.data]);

  const setGroups = useCallback((updater: (current: GroupsV2CardData[]) => GroupsV2CardData[]) => {
    setGroupsState((current) => ({ ...current, data: updater(current.data ?? []) }));
  }, []);
  const setAchievements = useCallback((items: Achievement[]) => {
    setAchievementsState(successResource(items));
  }, []);

  return {
    home,
    groups,
    achievements,
    onboarding,
    blockedAccount,
    reloadCritical,
    retryGroups,
    retryAchievements,
    retryOnboarding,
    setGroups,
    setAchievements,
  };
}
