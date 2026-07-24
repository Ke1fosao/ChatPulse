import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { appPaths } from "../../routing/paths";
import { initTelegram, notify } from "../../telegram/sdk";
import { OwnerApiError, ownerApi } from "../ownerApi";
import type { OwnerAuditEntry, OwnerGroup, OwnerOverviewData, OwnerSession, OwnerTab, OwnerUser, OwnerUserFilters } from "../types";

export const initialUserFilters: OwnerUserFilters = {
  query: "", vip: "all", status: "all", role: "all", payment: "all", tag: "",
  sort: "activity_desc", limit: 50, offset: 0,
};

function ownerTabFromPath(pathname: string): OwnerTab {
  if (pathname.startsWith(appPaths.owner.users)) return "users";
  if (pathname.startsWith(appPaths.owner.groups)) return "groups";
  if (pathname.startsWith(appPaths.owner.payments)) return "payments";
  if (pathname.startsWith(appPaths.owner.audit)) return "audit";
  return "overview";
}

const ownerTabPaths: Record<OwnerTab, string> = {
  overview: appPaths.owner.root, users: appPaths.owner.users, groups: appPaths.owner.groups,
  payments: appPaths.owner.payments, audit: appPaths.owner.audit,
};

export function useOwnerWorkspace() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = ownerTabFromPath(location.pathname);
  const [session, setSession] = useState<OwnerSession | null>(null);
  const [overview, setOverview] = useState<OwnerOverviewData | null>(null);
  const [users, setUsers] = useState<OwnerUser[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [userFilters, setUserFilters] = useState<OwnerUserFilters>(initialUserFilters);
  const [groups, setGroups] = useState<OwnerGroup[]>([]);
  const [groupsTotal, setGroupsTotal] = useState(0);
  const [audit, setAudit] = useState<OwnerAuditEntry[]>([]);
  const [groupQuery, setGroupQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState("");

  const loadUsers = useCallback(async () => {
    const payload = await ownerApi.users(userFilters);
    setUsers(payload.items); setUsersTotal(payload.total);
  }, [userFilters]);
  const loadGroups = useCallback(async () => {
    const payload = await ownerApi.groups(groupQuery, 50, 0);
    setGroups(payload.items); setGroupsTotal(payload.total);
  }, [groupQuery]);
  const loadAudit = useCallback(async () => setAudit((await ownerApi.audit(75)).items), []);
  const refreshOverview = useCallback(async () => setOverview(await ownerApi.overview()), []);

  const boot = useCallback(async () => {
    setLoading(true); setError(""); setForbidden(false);
    try {
      const ownerSession = await ownerApi.session();
      setSession(ownerSession);
      const userPayload = await ownerApi.users(initialUserFilters);
      setUsers(userPayload.items); setUsersTotal(userPayload.total);
      if (ownerSession.actor.is_owner) {
        const [overviewPayload, groupPayload, auditPayload] = await Promise.all([
          ownerApi.overview(), ownerApi.groups("", 50, 0), ownerApi.audit(75),
        ]);
        setOverview(overviewPayload); setGroups(groupPayload.items);
        setGroupsTotal(groupPayload.total); setAudit(auditPayload.items);
      } else {
        setOverview(null); setGroups([]); setAudit([]);
        navigate(appPaths.owner.users, { replace: true });
      }
      notify("success");
    } catch (reason) {
      const status = reason instanceof OwnerApiError ? reason.status
        : typeof reason === "object" && reason !== null && "status" in reason ? Number(reason.status) : 0;
      if (status === 401 || status === 403) setForbidden(true);
      setError(reason instanceof Error ? reason.message : "Owner Panel недоступна.");
      notify("error");
    } finally { setLoading(false); }
  }, [navigate]);

  useEffect(() => { initTelegram(); void boot(); }, [boot]);
  useEffect(() => {
    if (!session || activeTab !== "users") return;
    const timer = window.setTimeout(() => {
      setBusy(true);
      void loadUsers().catch((reason) => setError(reason instanceof Error ? reason.message : "Не вдалося оновити користувачів."))
        .finally(() => setBusy(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [activeTab, loadUsers, session]);
  useEffect(() => {
    if (!session?.actor.is_owner || activeTab !== "groups") return;
    const timer = window.setTimeout(() => {
      setBusy(true);
      void loadGroups().catch((reason) => setError(reason instanceof Error ? reason.message : "Не вдалося оновити групи."))
        .finally(() => setBusy(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [activeTab, loadGroups, session]);

  const refreshUsersAfterMutation = useCallback(async () => {
    if (!session) return;
    setBusy(true);
    try {
      const requests: Array<Promise<unknown>> = [loadUsers()];
      if (session.actor.is_owner) requests.push(refreshOverview(), loadAudit());
      await Promise.all(requests); notify("success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося оновити дані користувача.");
      notify("error"); throw reason;
    } finally { setBusy(false); }
  }, [loadAudit, loadUsers, refreshOverview, session]);

  const updateGroup = useCallback(async (chatId: number, values: Partial<OwnerGroup>) => {
    setBusy(true);
    try {
      await ownerApi.updateGroup(chatId, values);
      await Promise.all([loadGroups(), refreshOverview(), loadAudit()]); notify("success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося оновити групу.");
      notify("error"); throw reason;
    } finally { setBusy(false); }
  }, [loadAudit, loadGroups, refreshOverview]);

  return { activeTab, audit, busy, error, forbidden, groupQuery, groups, groupsTotal, loading,
    overview, session, userFilters, users, usersTotal, loadAudit, loadGroups, navigate,
    navigateTab: (tab: OwnerTab) => navigate(ownerTabPaths[tab]), refreshUsersAfterMutation,
    setError, setGroupQuery, setUserFilters, updateGroup };
}

export type OwnerWorkspace = ReturnType<typeof useOwnerWorkspace>;
