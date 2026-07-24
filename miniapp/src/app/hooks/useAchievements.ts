import { useCallback, useState } from "react";
import { api } from "../../api/client";
import type { Achievement } from "../../api/types";

export function useAchievements(setAchievements: (items: Achievement[]) => void) {
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setAchievements(await api.achievements());
    } finally {
      setLoading(false);
    }
  }, [setAchievements]);

  return { loading, refresh };
}
