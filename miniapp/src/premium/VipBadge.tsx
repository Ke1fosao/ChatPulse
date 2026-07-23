import { Crown, Star } from "lucide-react";
import type { AccountAccess } from "../api/types";

export function VipBadge({ account, compact = false }: { account: AccountAccess; compact?: boolean }) {
  if (!account.is_owner && !account.is_vip) return null;
  const owner = account.is_owner;
  const Icon = owner ? Crown : Star;
  return (
    <span className={`vip-inline-badge ${owner ? "is-owner" : "is-vip"} ${compact ? "is-compact" : ""}`}>
      <Icon size={compact ? 11 : 13} />
      <strong>{owner ? "OWNER" : "VIP"}</strong>
    </span>
  );
}
