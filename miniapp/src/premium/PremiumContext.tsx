import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { AccountAccess } from "../api/types";
import { premiumApi } from "./premiumApi";
import type { PremiumContextPayload } from "./types";

const freeAccount: AccountAccess = {
  plan: "free",
  is_owner: false,
  is_vip: false,
  vip_expires_at: null,
  entitlements: [],
};

interface PremiumState {
  account: AccountAccess;
  trialAvailable: boolean;
  loading: boolean;
  has(entitlement: string): boolean;
  refresh(): Promise<void>;
  openVip(source: string, featureKey?: string | null): void;
}

function navigateToVip(source: string, featureKey?: string | null): void {
  const params = new URLSearchParams({ source });
  if (featureKey) params.set("feature", featureKey);
  window.location.assign(`/miniapp/vip?${params.toString()}`);
}

const fallbackState: PremiumState = {
  account: freeAccount,
  trialAvailable: false,
  loading: false,
  has: () => false,
  refresh: async () => undefined,
  openVip: navigateToVip,
};

const PremiumContext = createContext<PremiumState | null>(null);

export function PremiumProvider({ children }: { children: ReactNode }) {
  const [payload, setPayload] = useState<PremiumContextPayload | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setPayload(await premiumApi.context());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh().catch(() => setLoading(false));
  }, [refresh]);

  const account = payload?.account ?? freeAccount;
  const has = useCallback(
    (entitlement: string) =>
      account.is_owner ||
      account.entitlements.includes("premium.all") ||
      account.entitlements.includes(entitlement),
    [account],
  );

  const openVip = useCallback((source: string, featureKey?: string | null) => {
    void premiumApi.event({
      event_type: "vip_feature_previewed",
      source,
      feature_key: featureKey,
    });
    navigateToVip(source, featureKey);
  }, []);

  const value = useMemo<PremiumState>(
    () => ({
      account,
      trialAvailable: Boolean(payload?.trial_available),
      loading,
      has,
      refresh,
      openVip,
    }),
    [account, has, loading, openVip, payload?.trial_available, refresh],
  );

  return <PremiumContext.Provider value={value}>{children}</PremiumContext.Provider>;
}

export function usePremium(): PremiumState {
  return useContext(PremiumContext) ?? fallbackState;
}
