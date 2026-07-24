import { Ban, Crown, ShieldCheck, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { ownerApi } from "./ownerApi";
import type { OwnerUserDetail } from "./types";
import { UserActionBar } from "./users/UserActionBar";
import { UserActionSheet } from "./users/UserActionSheet";
import { UserDrawerContent } from "./users/UserDrawerContent";
import { UserDrawerHeader } from "./users/UserDrawerHeader";
import { UserDrawerTabs } from "./users/UserDrawerTabs";
import type { DrawerTab, UserAction } from "./users/types";
interface OwnerUserDrawerProps { userId: number | null; permissions: string[]; onClose(): void; onChanged(): void | Promise<void>; }
const dateTime = new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium", timeStyle: "short" });
function formatDate(value?: string | null): string { return value ? dateTime.format(new Date(value)) : "—"; }
export function OwnerUserDrawer({ userId, permissions, onClose, onChanged }: OwnerUserDrawerProps) {
  const [detail, setDetail] = useState<OwnerUserDetail | null>(null); const [tab, setTab] = useState<DrawerTab>("overview"); const [action, setAction] = useState<UserAction>(null); const [loading, setLoading] = useState(false); const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  const can = useCallback((permission: string) => permissions.includes(permission), [permissions]);
  const load = useCallback(async () => { if (userId === null) return; setLoading(true); setError(""); try { setDetail(await ownerApi.userDetail(userId)); } catch (reasonValue) { setError(reasonValue instanceof Error ? reasonValue.message : "Не вдалося відкрити користувача."); } finally { setLoading(false); } }, [userId]);
  useEffect(() => { if (userId === null) return; document.body.classList.add("owner-modal-open"); document.body.style.overflow = "hidden"; void load(); return () => { document.body.classList.remove("owner-modal-open"); document.body.style.overflow = ""; }; }, [load, userId]);
  useEffect(() => { if (userId === null) { setDetail(null); setAction(null); setTab("overview"); setError(""); } }, [userId]);
  const run = async (task: () => Promise<unknown>) => { setSaving(true); setError(""); try { await task(); await Promise.all([load(), Promise.resolve(onChanged())]); setAction(null); } catch (reasonValue) { setError(reasonValue instanceof Error ? reasonValue.message : "Не вдалося зберегти зміну."); } finally { setSaving(false); } };
  if (userId === null) return null;
  return createPortal(<div className="owner-user-drawer-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) onClose(); }}><section className="owner-user-drawer" role="dialog" aria-modal="true" aria-label="Картка користувача"><UserDrawerHeader detail={detail} userId={userId} saving={saving} onClose={onClose} />{loading && !detail ? <div className="owner-empty">Завантаження картки…</div> : null}{error ? <button type="button" className="owner-error-banner" onClick={() => setError("")}>{error}</button> : null}{detail ? <><div className="owner-user-status-row"><span className={detail.is_blocked ? "is-danger" : "is-ok"}>{detail.is_blocked ? <Ban size={13} /> : <ShieldCheck size={13} />}{detail.is_blocked ? "Заблокований" : "Активний"}</span><span className={detail.vip.is_active ? "is-vip" : ""}><Crown size={13} /> {detail.vip.is_active ? "VIP" : "Free"}</span><span><Zap size={13} /> {detail.global_xp_total.toLocaleString("uk-UA")} XP</span></div><UserDrawerTabs active={tab} onChange={setTab} /><UserDrawerContent detail={detail} tab={tab} saving={saving} can={can} formatDate={formatDate} onRemoveTag={(tag) => void run(() => ownerApi.removeTag(detail.telegram_id, tag))} /><UserActionBar detail={detail} can={can} onAction={setAction} />{action ? <UserActionSheet key={action} action={action} detail={detail} saving={saving} onClose={() => setAction(null)} onRun={(task) => void run(task)} /> : null}</> : null}</section></div>, document.body);
}
