import type { ReactNode } from "react";
import type { AccountAccess } from "../api/types";

interface VipGateProps {
  account: AccountAccess;
  entitlement: string;
  preview: ReactNode;
  children: ReactNode;
}

export function VipGate({ account, entitlement, preview, children }: VipGateProps) {
  const unlocked =
    account.is_owner ||
    account.entitlements.includes("premium.all") ||
    account.entitlements.includes(entitlement);
  return <>{unlocked ? children : preview}</>;
}
