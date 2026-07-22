import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import type { AchievementEventPayload, AchievementRarity } from "../../api/types";

const rarityWeight: Record<AchievementRarity, number> = {
  common: 1,
  uncommon: 2,
  rare: 3,
  epic: 4,
  legendary: 5,
  secret: 6,
};

function mergeEvents(
  current: AchievementEventPayload[],
  incoming: AchievementEventPayload[],
): AchievementEventPayload[] {
  const merged = new Map(current.map((item) => [item.event_id, item]));
  for (const item of incoming) merged.set(item.event_id, item);
  return [...merged.values()].sort((left, right) => left.event_id - right.event_id);
}

export function useAchievementCelebrations() {
  const [queue, setQueue] = useState<AchievementEventPayload[]>([]);
  const [individualShown, setIndividualShown] = useState(0);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const events = await api.achievementEvents(10);
      setQueue((current) => mergeEvents(current, events));
    } catch {
      // Celebration delivery is non-blocking. The next poll retries safely.
    }
  }, []);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), 20_000);
    const onVisibility = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [refresh]);

  const summaryMode = individualShown >= 3 && queue.length > 0;
  const current = summaryMode ? null : queue[0] ?? null;
  const summaryItems = useMemo(
    () =>
      [...queue]
        .sort(
          (left, right) =>
            rarityWeight[right.achievement.rarity] - rarityWeight[left.achievement.rarity],
        )
        .slice(0, 3),
    [queue],
  );

  useEffect(() => {
    const active = queue.length > 0;
    document.body.classList.toggle("achievement-celebration-open", active);
    return () => document.body.classList.remove("achievement-celebration-open");
  }, [queue.length]);

  const dismissCurrent = useCallback(async () => {
    if (!current || busy) return;
    setBusy(true);
    try {
      await api.markAchievementSeen(current.event_id);
      setQueue((items) => items.filter((item) => item.event_id !== current.event_id));
      setIndividualShown((value) => value + 1);
    } finally {
      setBusy(false);
    }
  }, [busy, current]);

  const dismissSummary = useCallback(async () => {
    if (!summaryMode || busy) return;
    setBusy(true);
    try {
      await Promise.all(queue.map((item) => api.markAchievementSeen(item.event_id)));
      setQueue([]);
      setIndividualShown(0);
    } finally {
      setBusy(false);
    }
  }, [busy, queue, summaryMode]);

  useEffect(() => {
    if (queue.length === 0 && individualShown !== 0) setIndividualShown(0);
  }, [individualShown, queue.length]);

  const shareCurrent = useCallback(async () => {
    if (!current) return;
    const text = [
      "🏆 Нове досягнення в ChatPulse!",
      current.achievement.title,
      current.achievement.description,
      current.achievement.group_title
        ? `Група: ${current.achievement.group_title}`
        : "Глобальне досягнення",
    ].join("\n");

    try {
      if (navigator.share) {
        await navigator.share({ title: current.achievement.title, text });
      } else {
        await navigator.clipboard.writeText(text);
      }
      await api.markAchievementShared(current.event_id);
    } catch {
      // A cancelled native share should not close or acknowledge the celebration.
    }
  }, [current]);

  return {
    active: queue.length > 0,
    busy,
    current,
    summaryMode,
    summaryCount: queue.length,
    summaryItems,
    dismissCurrent,
    dismissSummary,
    shareCurrent,
    refresh,
  };
}
