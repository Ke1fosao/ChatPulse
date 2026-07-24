import { X } from "lucide-react";
import type { OwnerUserDetail } from "../types";
export function UserDrawerHeader({ detail, userId, saving, onClose }: { detail: OwnerUserDetail | null; userId: number; saving: boolean; onClose(): void }) {
  return <header className="owner-user-drawer__header"><div className="owner-user-drawer__avatar">{detail?.display_name.slice(0, 2).toUpperCase() ?? "…"}</div><div><p>{detail?.role ? detail.role.toUpperCase() : "КОРИСТУВАЧ"}</p><h3>{detail?.display_name ?? "Завантаження…"}</h3><small>{detail?.username ? `@${detail.username}` : `ID ${userId}`}</small></div><button type="button" aria-label="Закрити картку" onClick={onClose} disabled={saving}><X size={19} /></button></header>;
}
