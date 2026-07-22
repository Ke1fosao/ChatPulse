import { AlertTriangle, Crown, LockKeyhole, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { initTelegram, isTelegramContext, notify } from "../telegram/sdk";
import { OwnerAudit } from "./OwnerAudit";
import { OwnerGroups } from "./OwnerGroups";
import { OwnerOverview } from "./OwnerOverview";
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
  VipFilter,
  VipGrantPayload,
  VipRevokePayload,
} from "./types";

export function OwnerApp() {
  const [session, setSession] = useState<OwnerSession | null>(null);
  const [overview, setOverview] = useState<OwnerOverviewData | null>(null);
  const [users, setUsers] = useState<OwnerUser[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [groups, setGroups] = useState<OwnerGroup[]>([]);
  const [groupsTotal, setGroupsTotal] = useState(0);
  const [audit, setAudit] = useState<OwnerAuditEntry[]>([]);
  const [activeTab, setActiveTab] = useState<OwnerTab>("overview");
  const [query, setQuery] = useState("");
  const [groupQuery, setGroupQuery] = useState("");
  const [vipFilter, setVipFilter] = useState<VipFilter>("all");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState("");

  const loadUsers = useCallback(async () => {
    const payload = await ownerApi.users(query, vipFilter, 50, 0);
    setUsers(payload.items);
    setUsersTotal(payload.total);
  }, [query, vipFilter]);

  const loadGroups = useCallback(async () => {
    const payload = await ownerApi.groups(groupQuery, 50, 0);
    setGroups(payload.items);
    setGroupsTotal(payload.total);
  }, [groupQuery]);

  const loadAudit = useCallback(async () => {
    const payload = await ownerApi.audit(75);
    setAudit(payload.items);
  }, []);

  const boot = useCallback(async () => {
    setLoading(true);
    setError("");
    setForbidden(false);
    try {
      const ownerSession = await ownerApi.session();
      setSession(ownerSession);
      const [overviewPayload, userPayload, groupPayload, auditPayload] = await Promise.all([
        ownerApi.overview(),
        ownerApi.users("", "all", 50, 0),
        ownerApi.groups("", 50, 0),
        ownerApi.audit(75),
      ]);
      setOverview(overviewPayload);
      setUsers(userPayload.items);
      setUsersTotal(userPayload.total);
      setGroups(groupPayload.items);
      setGroupsTotal(groupPayload.total);
      setAudit(auditPayload.items);
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
    if (!session || activeTab !== "groups") return;
    const timer = window.setTimeout(() => {
      setBusy(true);
      void loadGroups()
        .catch((reason) => setError(reason instanceof Error ? reason.message : "Не вдалося оновити групи."))
        .finally(() => setBusy(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [activeTab, loadGroups, session]);

  const refreshOverview = async () => {
    setOverview(await ownerApi.overview());
  };

  const grantVip = async (userId: number, payload: VipGrantPayload) => {
    setBusy(true);
    try {
      await ownerApi.grantVip(userId, payload);
      await Promise.all([loadUsers(), refreshOverview(), loadAudit()]);
      notify("success");
    } finally {
      setBusy(false);
    }
  };

  const revokeVip = async (userId: number, payload: VipRevokePayload) => {
    setBusy(true);
    try {
      await ownerApi.revokeVip(userId, payload);
      await Promise.all([loadUsers(), refreshOverview(), loadAudit()]);
      notify("success");
    } finally {
      setBusy(false);
    }
  };

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
    if (!overview) return null;
    if (activeTab === "users") {
      return (
        <OwnerUsers
          users={users}
          total={usersTotal}
          loading={busy}
          query={query}
          vipFilter={vipFilter}
          onQueryChange={setQuery}
          onVipFilterChange={setVipFilter}
          onRefresh={() => void loadUsers()}
          onGrant={grantVip}
          onRevoke={revokeVip}
        />
      );
    }
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
    if (activeTab === "audit") {
      return <OwnerAudit items={audit} loading={busy} onRefresh={() => void loadAudit()} />;
    }
    return <OwnerOverview data={overview} />;
  }, [
    activeTab,
    audit,
    busy,
    groupQuery,
    groups,
    groupsTotal,
    loadAudit,
    loadGroups,
    loadUsers,
    overview,
    query,
    users,
    usersTotal,
    vipFilter,
  ]);

  if (!isTelegramContext()) {
    return (
      <main className="owner-gate">
        <LockKeyhole size={34} />
        <h1>Відкрий Owner Panel через Telegram</h1>
        <p>Авторизація власника працює лише через підписаний Telegram Mini App session.</p>
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
        <p>{error || "Цей маршрут доступний лише єдиному власнику ChatPulse."}</p>
        <button type="button" onClick={() => window.location.assign("/miniapp")}>Повернутися в ChatPulse</button>
      </main>
    );
  }

  return (
    <OwnerShell session={session} activeTab={activeTab} onTabChange={setActiveTab} busy={busy}>
      {error ? (
        <button type="button" className="owner-error-banner" onClick={() => setError("")}>
          <AlertTriangle size={16} /> {error}
        </button>
      ) : null}
      {page ?? (
        <div className="owner-empty">
          <RefreshCw size={20} /> Не вдалося завантажити огляд.
          <button type="button" onClick={() => void boot()}>Повторити</button>
        </div>
      )}
    </OwnerShell>
  );
}
