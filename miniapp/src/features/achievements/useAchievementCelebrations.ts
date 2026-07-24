import { useCallback, useEffect, useMemo, useState } from "react";
import { api, downloadBlob } from "../../api/client";
import type {
  Achievement,
  AchievementEventPayload,
  AchievementRarity,
  AchievementUnlockEventPayload,
} from "../../api/types";
import { notify } from "../../telegram/sdk";
import { vipApi } from "../../vip/vipApi";

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

function isUnlockEvent(
  event: AchievementEventPayload,
): event is AchievementUnlockEventPayload {
  return event.event_type === "unlock";
}

export function useAchievementCelebrations() {
  const [queue, setQueue] = useState<AchievementEventPayload[]>([]);
  const [individualShown, setIndividualShown] = useState(0);
  const [busy, setBusy] = useState(false);
  const [pinned, setPinned] = useState(false);

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

  const head = queue[0] ?? null;
  const collectionUpdate = head?.event_type === "collection_update" ? head : null;
  const summaryMode = collectionUpdate !== null || (individualShown >= 3 && queue.length > 0);
  const current = !summaryMode && head && isUnlockEvent(head) ? head : null;
  const summaryItems = useMemo<Achievement[]>(() => {
    if (collectionUpdate) return collectionUpdate.summary.achievements;
    return queue
      .filter(isUnlockEvent)
      .map((item) => item.achievement)
      .sort(
        (left, right) => rarityWeight[right.rarity] - rarityWeight[left.rarity],
      )
      .slice(0, 3);
  }, [collectionUpdate, queue]);
  const summaryCount = collectionUpdate?.summary.count ?? queue.length;

  useEffect(() => {
    setPinned(false);
  }, [current?.event_id]);

  useEffect(() => {
    const blocking =
      summaryMode ||
      Boolean(
        current &&
          ["rare", "epic", "legendary", "secret"].includes(
            current.achievement.rarity,
          ),
      );
    document.body.classList.toggle("achievement-celebration-open", blocking);
    return () => document.body.classList.remove("achievement-celebration-open");
  }, [current, summaryMode]);

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
    const eventIds = collectionUpdate
      ? [collectionUpdate.event_id]
      : queue.map((item) => item.event_id);
    setBusy(true);
    try {
      await Promise.all(eventIds.map((eventId) => api.markAchievementSeen(eventId)));
      setQueue((items) =>
        items.filter((item) => !eventIds.includes(item.event_id)),
      );
      setIndividualShown(0);
    } finally {
      setBusy(false);
    }
  }, [busy, collectionUpdate, queue, summaryMode]);

  useEffect(() => {
    if (queue.length === 0 && individualShown !== 0) setIndividualShown(0);
  }, [individualShown, queue.length]);

  const shareCurrent = useCallback(async () => {
    if (!current || busy) return;
    const text = [
      "🏆 Нове досягнення в ChatPulse!",
      current.achievement.title,
      current.achievement.description,
      current.achievement.group_title
        ? `Група: ${current.achievement.group_title}`
        : "Глобальне досягнення",
    ].join("\n");
    const filename = `chatpulse-${current.achievement.code}.png`;

    setBusy(true);
    try {
      const blob = await api.achievementCard(current.event_id);
      const file = new File([blob], filename, { type: "image/png" });
      const fileShare = { files: [file], title: current.achievement.title, text };

      if (navigator.share && navigator.canShare?.({ files: [file] })) {
        await navigator.share(fileShare);
      } else {
        downloadBlob(blob, filename);
        try {
          await navigator.clipboard.writeText(text);
        } catch {
          // PNG download is still a successful fallback when clipboard is blocked.
        }
      }
      await api.markAchievementShared(current.event_id);
    } catch {
      // A cancelled native share or failed download keeps the celebration open.
    } finally {
      setBusy(false);
    }
  }, [busy, current]);

  const pinCurrent = useCallback(async () => {
    const achievement = current?.achievement;
    const scopeKey = achievement?.primary_scope_key;
    if (!achievement || !scopeKey || busy || pinned) return;
    setBusy(true);
    try {
      const featured = await vipApi.featured();
      const existing = featured.map((item) => ({
        code: item.code,
        scope_key: item.scope_key,
      }));
      if (
        existing.some(
          (item) => item.code === achievement.code && item.scope_key === scopeKey,
        )
      ) {
        setPinned(true);
        return;
      }
      if (existing.length >= 5) {
        notify("warning");
        return;
      }
      await vipApi.updateFeatured([
        ...existing,
        { code: achievement.code, scope_key: scopeKey },
      ]);
      setPinned(true);
      notify("success");
    } catch {
      notify("warning");
    } finally {
      setBusy(false);
    }
  }, [busy, current, pinned]);

  return {
    active: queue.length > 0,
    busy,
    pinned,
    current,
    summaryMode,
    historicalSummary: collectionUpdate !== null,
    summaryCount,
    summaryItems,
    dismissCurrent,
    dismissSummary,
    shareCurrent,
    pinCurrent,
    refresh,
  };
}
