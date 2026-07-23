import { AlertTriangle, Crown, LockKeyhole, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { initTelegram, isTelegramContext, notify } from "../telegram/sdk";
import { OwnerAudit } from "./OwnerAudit";
import { OwnerGroups } from "./OwnerGroups";
import { OwnerOverview } from "./OwnerOverview";
import { OwnerPayments } from "./OwnerPayments";
import { OwnerShell } from "./OwnerShell";
import { OwnerUsers } from "./OwnerUsers";
import { OwnerApiError, ownerApi } from "./ownerApi";
import type {
  OwnerAuditEntry,
  OwnerGroup,
  OwnerOverviewData,
  OwnerSession,
  OwnerTab,
  OwnerUser,
  OwnerUserFilters,
} from "./types";

const initialUserFilters: OwnerUserFilters = {
  query: "",
  vip: "all",
  status: "all",
  role: "all",
  payment: "all",
  tag: "",
  sort: "activity_desc",
  limit: 50,
  offset: 0,
};

export function OwnerApp() {
  const [session, setSession] = useState<OwnerSession | null>(null);
  const [overview, setOverview] = useState<OwnerOverviewData | null>(null);
  const [users, setUsers] = useState<OwnerUser[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [userFilters, setUserFilters] = useState<OwnerUserFilters>(initialUserFilters);
  const [groups, setGroups] = useState<OwnerGroup[]>([]);
  const [groupsTotal, setGroupsTotal] = useState(0);
  const [audit, setAudit] = useState<OwnerAuditEntry[]>([]);
  const [activeTab, setActiveTab] = useState<OwnerTab>("overview");
  const [groupQuery, setGroupQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState("");

  const loadUsers = useCallback(async () => {
    const payload = await ownerApi.users(userFilters);
    setUsers(payload.items);
    setUsersTotal(payload.total);
  }, [userFilters]);

  const loadGroups = useCallback(async () => {
    const payload = await ownerApi.groups(groupQuery, 50, 0);
    setGroups(payload.items);
    setGroupsTotal(payload.total);
  }, [groupQuery]);

  const loadAudit = useCallback(async () => {
    const payload = await ownerApi.audit(75);
    setAudit(payload.items);
  }, []);

  const refreshOverview = useCallback(async () => {
    setOverview(await ownerApi.overview());
  }, []);

  const boot = useCallback(async () => {
    setLoading(true);
    setError("");
    setForbidden(false);
    try {
      const ownerSession = await ownerApi.session();
      setSession(ownerSession);
      const userPayload = await ownerApi.users(initialUserFilters);
      setUsers(userPayload.items);
      setUsersTotal(userPayload.total);

      if (ownerSession.actor.is_owner) {
        const [overviewPayload, groupPayload, auditPayload] = await Promise.all([
          ownerApi.overview(),
          ownerApi.groups("", 50, 0),
          ownerApi.audit(75),
        ]);
        setOverview(overviewPayload);
        setGroups(groupPayload.items);
        setGroupsTotal(groupPayload.total);
        setAudit(auditPayload.items);
        setActiveTab("overview");
      } else {
        setOverview(null);
        setGroups([]);
        setAudit([]);
        setActiveTab("users");
      }
      notify("success");
    } catch (reason) {
      const status = reason instanceof OwnerApiError
        ? reason.status
        : typeof reason === "object" && reason !== null && "status" in reason
          ? Number(reason.status)
          : 0;
      if (status === 401 || status === 403) setForbidden(true);
      setError(reason instanceof Error ? reason.message : "Owner Panel недоступна.");
      notify("error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    initTelegram();
    void boot();
  }, [boot]);

  useEffect(() => {
    if (!session || activeTab !== "users") return;
    const timer = window.setTimeout(() => {
      setBusy(true);
      void loadUsers()
        .catch((reason) => setError(reason instanceof Error ? reason.message : "Не вдалося оновити користувачів."))
        .finally(() => setBusy(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [activeTab, loadUsers, session]);

  useEffect(() => {
    if (!session?.actor.is_owner || activeTab !== "groups") return;
    const timer = window.setTimeout(() => {
      setBusy(true);
      void loadGroups()
        .catch((reason) => setError(reason instanceof Error ? reason.message : "Не вдалося оновити групи."))
        .finally(() => setBusy(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [activeTab, loadGroups, session]);

  const refreshUsersAfterMutation = useCallback(async () => {
    if (!session) return;
    setBusy(true);
    try {
      const requests: Array<Promise<unknown>> = [loadUsers()];
      if (session.actor.is_owner) {
        requests.push(refreshOverview(), loadAudit());
      }
      await Promise.all(requests);
      notify("success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не вдалося оновити дані користувача.");
      notify("error");
      throw reason;
    } finally {
      setBusy(false);
    }
  }, [loadAudit, loadUsers, refreshOverview, session]);

  const updateGroup = async (chatId: number, values: Partial<OwnerGroup>) => {
    setBusy(true);
    try {
      await ownerApi.updateGroup(chatId, values);
      await Promise.all([loadGroups(), refreshOverview(), loadAudit()]);
      notify("success");
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Не вдалося оновити групу.";
      setError(message);
      notify("error");
      throw reason;
    } finally {
      setBusy(false);
    }
  };

  const page = useMemo(() => {
    if (!session) return null;
    if (activeTab === "users") {
      return (
        <OwnerUsers
          users={users}
          total={usersTotal}
          loading={busy}
          filters={userFilters}
          permissions={session.actor.permissions}
          onFiltersChange={setUserFilters}
          onRefresh={refreshUsersAfterMutation}
        />
      );
    }
    if (!session.actor.is_owner) return null;
    if (activeTab === "groups") {
      return (
        <OwnerGroups
          groups={groups}
          total={groupsTotal}
          loading={busy}
          query={groupQuery}
          onQueryChange={setGroupQuery}
          onRefresh={() => void loadGroups()}
          onUpdate={updateGroup}
        />
      );
    }
    if (activeTab === "payments") return <OwnerPayments />;
    if (activeTab === "audit") {
      return <OwnerAudit items={audit} loading={busy} onRefresh={() => void loadAudit()} />;
    }
    return overview ? <OwnerOverview data={overview} /> : null;
  }, [
    activeTab,
    audit,
    busy,
    groupQuery,
    groups,
    groupsTotal,
    loadAudit,
    loadGroups,
    overview,
    refreshUsersAfterMutation,
    session,
    userFilters,
    users,
    usersTotal,
  ]);

  if (!isTelegramContext()) {
    return (
      <main className="owner-gate">
        <LockKeyhole size={34} />
        <h1>Відкрий Owner Panel через Telegram</h1>
        <p>Захищена авторизація працює лише через підписану Telegram Mini App session.</p>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="owner-gate owner-gate--loading">
        <Crown size={34} />
        <h1>Owner Control</h1>
        <p>Перевіряємо захищений доступ…</p>
        <div className="owner-loader"><span /></div>
      </main>
    );
  }

  if (forbidden || !session) {
    return (
      <main className="owner-gate owner-gate--danger">
        <LockKeyhole size={34} />
        <h1>Owner Panel закрито</h1>
        <p>{error || "Цей маршрут доступний лише команді ChatPulse."}</p>
        <button type="button" onClick={() => window.location.assign("/miniapp")}>Повернутися в ChatPulse</button>
      </main>
    );
  }

  return (
    <OwnerShell session={session} activeTab={activeTab} onTabChange={setActiveTab} busy={busy}>
      {error ? (
        <button type="button" className="owner-error-banner" onClick={() => setError("") }>
          <AlertTriangle size={16} /> {error}
        </button>
      ) : null}
      {page ?? (
        <div className="owner-empty">
          <RefreshCw size={20} /> Цей розділ недоступний для вашої ролі.
          <button type="button" onClick={() => setActiveTab("users")}>До користувачів</button>
        </div>
      )}
    </OwnerShell>
  );
}
