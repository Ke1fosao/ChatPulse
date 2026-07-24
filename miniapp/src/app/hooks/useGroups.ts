import { useCallback } from "react";
import { api } from "../../api/client";
import type { GroupsV2CardData } from "../../api/groups-v2";
import { notify } from "../../telegram/sdk";

export function useGroups(
  setGroups: React.Dispatch<React.SetStateAction<GroupsV2CardData[]>>,
  setError: (message: string) => void,
) {
  const toggleFavorite = useCallback(async (group: GroupsV2CardData, nextValue: boolean) => {
    setGroups((current) => current.map((item) =>
      item.telegram_chat_id === group.telegram_chat_id ? { ...item, is_favorite: nextValue } : item,
    ));
    try {
      await api.setGroupFavorite(group.telegram_chat_id, nextValue);
      notify("success");
    } catch (reason) {
      setGroups((current) => current.map((item) =>
        item.telegram_chat_id === group.telegram_chat_id ? { ...item, is_favorite: !nextValue } : item,
      ));
      setError(reason instanceof Error ? reason.message : "Не вдалося оновити обране.");
      notify("error");
      throw reason;
    }
  }, [setError, setGroups]);

  return { toggleFavorite };
}
