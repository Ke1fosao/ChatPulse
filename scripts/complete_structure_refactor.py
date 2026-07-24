from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def split_owner_routes() -> None:
    path = ROOT / "app/api/owner/routes.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    endpoints: list[tuple[str, str, str]] = []
    for node in tree.body:
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        route_path = None
        first_line = node.lineno
        for decorator in node.decorator_list:
            first_line = min(first_line, decorator.lineno)
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "router"
                and decorator.args
                and isinstance(decorator.args[0], ast.Constant)
                and isinstance(decorator.args[0].value, str)
            ):
                route_path = decorator.args[0].value
        if route_path is None:
            continue
        block = "".join(lines[first_line - 1 : node.end_lineno]).rstrip() + "\n"
        endpoints.append((route_path, node.name, block))
    if not endpoints:
        raise RuntimeError("No owner route endpoints found")
    first_endpoint_line = min(
        min(decorator.lineno for decorator in node.decorator_list)
        for node in tree.body
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
        and any(
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and isinstance(d.func.value, ast.Name)
            and d.func.value.id == "router"
            for d in node.decorator_list
        )
    )
    common = "".join(lines[: first_endpoint_line - 1])
    common = re.sub(
        r'\nrouter = APIRouter\(prefix="/api/owner/v1", tags=\["owner"\]\)\n',
        "\n",
        common,
        count=1,
    )
    write("app/api/owner/common.py", common)
    groups: dict[str, list[tuple[str, str]]] = {
        "session": [],
        "overview": [],
        "users": [],
        "groups": [],
        "payments": [],
        "audit": [],
    }
    for route_path, name, block in endpoints:
        if route_path == "/session":
            category = "session"
        elif route_path == "/overview":
            category = "overview"
        elif route_path.startswith("/users"):
            category = "users"
        elif route_path.startswith("/groups"):
            category = "groups"
        elif route_path.startswith("/payments"):
            category = "payments"
        elif route_path.startswith("/audit"):
            category = "audit"
        else:
            category = "overview"
        groups[category].append((name, block))
    helper_import = (
        "from .common import *  # noqa: F403\n"
        "from .common import (\n"
        "    _raise_repository_error,\n"
        "    _repository,\n"
        "    _send_user_message,\n"
        "    _user_repository,\n"
        "    _vip_service,\n"
        ")\n\n"
        "router = APIRouter()\n\n"
    )
    module_names: dict[str, list[str]] = {}
    for category, blocks in groups.items():
        if not blocks:
            continue
        module_names[category] = [name for name, _ in blocks]
        write(
            f"app/api/owner/{category}.py",
            helper_import + "\n\n".join(block for _, block in blocks),
        )
    route_lines = ["from fastapi import APIRouter", ""]
    for category in module_names:
        route_lines.append(f"from app.api.owner.{category} import router as {category}_router")
    route_lines.extend(["", 'router = APIRouter(prefix="/api/owner/v1", tags=["owner"])', ""])
    for category in module_names:
        route_lines.append(f"router.include_router({category}_router)")
    route_lines.append("")
    for category, names in module_names.items():
        route_lines.append(
            f"from app.api.owner.{category} import {', '.join(names)}  # noqa: E402,F401"
        )
    write("app/api/owner/routes.py", "\n".join(route_lines))


def split_user_control_repository() -> None:
    path = ROOT / "app/repositories/user_control.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    repository_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "UserControlRepository"
    )
    prefix = "".join(lines[: repository_class.lineno - 1]).rstrip() + "\n\n"
    methods: dict[str, str] = {}
    for node in repository_class.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        first_line = min((d.lineno for d in node.decorator_list), default=node.lineno)
        methods[node.name] = "".join(lines[first_line - 1 : node.end_lineno]).rstrip() + "\n"
    helper_nodes = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("_")
    ]
    base_method_names = [
        name
        for name in methods
        if name == "__init__" or name == "resolve_actor" or name.startswith("_")
    ]
    write(
        "app/repositories/user_control/base.py",
        prefix
        + "class UserControlBase:\n"
        + "\n\n".join(methods[name] for name in base_method_names),
    )
    public = [name for name in methods if name not in base_method_names]
    categories: dict[str, list[str]] = {
        "queries": [],
        "restrictions": [],
        "staff": [],
        "notes_tags": [],
        "xp": [],
        "messaging": [],
        "audit": [],
    }
    restriction_names = {
        "is_blocked",
        "get_block_info",
        "record_blocked_access",
        "block_user",
        "unblock_user",
    }
    for name in public:
        if name in restriction_names:
            category = "restrictions"
        elif "message" in name or "delivery" in name:
            category = "messaging"
        elif "role" in name or "staff" in name:
            category = "staff"
        elif "note" in name or "tag" in name:
            category = "notes_tags"
        elif "xp" in name:
            category = "xp"
        elif "audit" in name:
            category = "audit"
        else:
            category = "queries"
        categories[category].append(name)
    helper_imports = "from .base import " + ", ".join(helper_nodes) + "\n" if helper_nodes else ""
    class_names = {
        "queries": "UserQueriesMixin",
        "restrictions": "UserRestrictionsMixin",
        "staff": "UserStaffMixin",
        "notes_tags": "UserNotesTagsMixin",
        "xp": "UserXpMixin",
        "messaging": "UserMessagingMixin",
        "audit": "UserAuditMixin",
    }
    active_mixins: list[tuple[str, str]] = []
    for category, names in categories.items():
        if not names:
            continue
        class_name = class_names[category]
        active_mixins.append((category, class_name))
        write(
            f"app/repositories/user_control/{category}.py",
            "from .base import *  # noqa: F403\n"
            + helper_imports
            + "\n\n"
            + f"class {class_name}:\n"
            + "\n\n".join(methods[name] for name in names),
        )
    repository_imports = ["from .base import UserControlBase"]
    for category, class_name in active_mixins:
        repository_imports.append(f"from .{category} import {class_name}")
    inheritance = ", ".join(class_name for _, class_name in active_mixins) + ", UserControlBase"
    repository_imports.extend(
        ["", "", f"class UserControlRepository({inheritance}):", "    pass", ""]
    )
    write("app/repositories/user_control/repository.py", "\n".join(repository_imports))
    write(
        "app/repositories/user_control/__init__.py",
        "from .base import PaymentFilter, SortMode, StatusFilter, VipFilter\n"
        "from .repository import UserControlRepository\n\n"
        "__all__ = [\n"
        '    "PaymentFilter",\n    "SortMode",\n    "StatusFilter",\n'
        '    "UserControlRepository",\n    "VipFilter",\n]\n',
    )
    path.unlink()


OWNER_HOOK = r"""import { useCallback, useEffect, useState } from "react";
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
"""

OWNER_ROUTES = r"""import { Navigate, Route, Routes } from "react-router-dom";
import { appPaths } from "../routing/paths";
import { OwnerAudit } from "./OwnerAudit";
import { OwnerGroups } from "./OwnerGroups";
import { OwnerOverview } from "./OwnerOverview";
import { OwnerPayments } from "./OwnerPayments";
import { OwnerUsers } from "./OwnerUsers";
import type { OwnerWorkspace } from "./hooks/useOwnerWorkspace";

export function OwnerRoutes({ workspace }: { workspace: OwnerWorkspace }) {
  const { session } = workspace;
  if (!session) return null;
  return <Routes>
    <Route index element={session.actor.is_owner && workspace.overview ? <OwnerOverview data={workspace.overview} /> : <Navigate to="users" replace />} />
    <Route path="users/*" element={<OwnerUsers users={workspace.users} total={workspace.usersTotal} loading={workspace.busy} filters={workspace.userFilters} permissions={session.actor.permissions} onFiltersChange={workspace.setUserFilters} onRefresh={workspace.refreshUsersAfterMutation} />} />
    <Route path="groups" element={session.actor.is_owner ? <OwnerGroups groups={workspace.groups} total={workspace.groupsTotal} loading={workspace.busy} query={workspace.groupQuery} onQueryChange={workspace.setGroupQuery} onRefresh={() => void workspace.loadGroups()} onUpdate={workspace.updateGroup} /> : <Navigate to={appPaths.owner.users} replace />} />
    <Route path="payments" element={session.actor.is_owner ? <OwnerPayments /> : <Navigate to={appPaths.owner.users} replace />} />
    <Route path="audit" element={session.actor.is_owner ? <OwnerAudit items={workspace.audit} loading={workspace.busy} onRefresh={() => void workspace.loadAudit()} /> : <Navigate to={appPaths.owner.users} replace />} />
    <Route path="*" element={<Navigate to={appPaths.owner.users} replace />} />
  </Routes>;
}
"""

OWNER_APP = r"""import { AlertTriangle, Crown, LockKeyhole } from "lucide-react";
import { appPaths } from "../routing/paths";
import { isTelegramContext } from "../telegram/sdk";
import { useOwnerWorkspace } from "./hooks/useOwnerWorkspace";
import { OwnerRoutes } from "./OwnerRoutes";
import { OwnerShell } from "./OwnerShell";
import "./styles";

export function OwnerApp() {
  const workspace = useOwnerWorkspace();
  if (!isTelegramContext()) return <main className="owner-gate"><LockKeyhole size={34} /><h1>Відкрий Owner Panel через Telegram</h1><p>Захищена авторизація працює лише через підписану Telegram Mini App session.</p></main>;
  if (workspace.loading) return <main className="owner-gate owner-gate--loading"><Crown size={34} /><h1>Owner Control</h1><p>Перевіряємо захищений доступ…</p><div className="owner-loader"><span /></div></main>;
  if (workspace.forbidden || !workspace.session) return <main className="owner-gate owner-gate--danger"><LockKeyhole size={34} /><h1>Owner Panel закрито</h1><p>{workspace.error || "Цей маршрут доступний лише команді ChatPulse."}</p><button type="button" onClick={() => workspace.navigate(appPaths.home)}>Повернутися в ChatPulse</button></main>;
  return <OwnerShell session={workspace.session} activeTab={workspace.activeTab} onTabChange={workspace.navigateTab} busy={workspace.busy}>
    {workspace.error ? <button type="button" className="owner-error-banner" onClick={() => workspace.setError("")}><AlertTriangle size={16} /> {workspace.error}</button> : null}
    <OwnerRoutes workspace={workspace} />
  </OwnerShell>;
}
"""

USER_TYPES = 'export type DrawerTab = "overview" | "groups" | "payments" | "history";\nexport type UserAction = "vip" | "block" | "xp" | "role" | "note" | "tag" | "message" | null;\n'

USER_HEADER = r"""import { X } from "lucide-react";
import type { OwnerUserDetail } from "../types";
export function UserDrawerHeader({ detail, userId, saving, onClose }: { detail: OwnerUserDetail | null; userId: number; saving: boolean; onClose(): void }) {
  return <header className="owner-user-drawer__header"><div className="owner-user-drawer__avatar">{detail?.display_name.slice(0, 2).toUpperCase() ?? "…"}</div><div><p>{detail?.role ? detail.role.toUpperCase() : "КОРИСТУВАЧ"}</p><h3>{detail?.display_name ?? "Завантаження…"}</h3><small>{detail?.username ? `@${detail.username}` : `ID ${userId}`}</small></div><button type="button" aria-label="Закрити картку" onClick={onClose} disabled={saving}><X size={19} /></button></header>;
}
"""

USER_TABS = r"""import type { DrawerTab } from "./types";
const tabs: Array<[DrawerTab, string]> = [["overview", "Огляд"], ["groups", "Групи"], ["payments", "Платежі"], ["history", "Історія"]];
export function UserDrawerTabs({ active, onChange }: { active: DrawerTab; onChange(tab: DrawerTab): void }) {
  return <nav className="owner-user-tabs" aria-label="Розділи користувача">{tabs.map(([id, label]) => <button key={id} type="button" className={active === id ? "is-active" : ""} onClick={() => onChange(id)}>{label}</button>)}</nav>;
}
"""

USER_CONTENT = r"""import { Ban, History, MessageSquareText, Tag, Users } from "lucide-react";
import type { OwnerUserDetail } from "../types";
import type { DrawerTab } from "./types";
export function UserDrawerContent(props: { detail: OwnerUserDetail; tab: DrawerTab; saving: boolean; can(permission: string): boolean; formatDate(value?: string | null): string; onRemoveTag(tag: string): void }) {
  const { detail, tab } = props;
  return <div className="owner-user-drawer__body">
    {tab === "overview" ? <div className="owner-user-detail-grid"><article><small>Telegram ID</small><strong>{detail.telegram_id}</strong></article><article><small>Рівень</small><strong>{detail.global_level}</strong></article><article><small>Реєстрація</small><strong>{props.formatDate(detail.created_at)}</strong></article><article><small>Остання активність</small><strong>{props.formatDate(detail.last_activity_at)}</strong></article>{detail.is_blocked ? <section className="owner-user-warning"><Ban size={18} /><div><strong>Повний блок</strong><p>{detail.restriction?.reason || "Причину не вказано"}</p></div></section> : null}<section className="owner-user-note-card"><div><MessageSquareText size={16} /><strong>Приватна нотатка</strong></div><p>{detail.note || "Нотатки ще немає."}</p></section><section className="owner-user-tag-card"><div><Tag size={16} /><strong>Теги</strong></div><div className="owner-user-tags">{detail.tags.length ? detail.tags.map((item) => <button key={item} type="button" disabled={!props.can("users.notes") || props.saving} onClick={() => props.onRemoveTag(item)}>#{item} ×</button>) : <span>Немає тегів</span>}</div></section></div> : null}
    {tab === "groups" ? <div className="owner-user-history-list">{detail.groups.length ? detail.groups.map((group) => <article key={group.telegram_chat_id}><Users size={17} /><div><strong>{group.title}</strong><small>{group.xp_total} XP · рівень {group.level}</small></div><time>{props.formatDate(group.last_seen_at)}</time></article>) : <div className="owner-empty">Користувач поки не входить до груп.</div>}</div> : null}
    {tab === "payments" ? <div className="owner-user-payment-summary"><article><small>Усього Stars</small><strong>{detail.payment_summary.stars_total.toLocaleString("uk-UA")} ⭐</strong></article><article><small>Успішних оплат</small><strong>{detail.payment_summary.payment_count}</strong></article><article><small>Остання оплата</small><strong>{props.formatDate(detail.payment_summary.last_payment_at)}</strong></article><article><small>Підписка</small><strong>{detail.payment_summary.active_subscription ? "Активна" : "Немає"}</strong></article></div> : null}
    {tab === "history" ? <div className="owner-user-history-list">{detail.audit.length ? detail.audit.map((item) => <article key={item.id}><History size={17} /><div><strong>{item.action}</strong><small>Actor ID {item.actor_telegram_user_id}</small></div><time>{props.formatDate(item.created_at)}</time></article>) : <div className="owner-empty">Історія змін порожня.</div>}</div> : null}
  </div>;
}
"""

USER_ACTION_BAR = r"""import { Ban, Crown, MessageSquareText, Tag, UserCog, Zap } from "lucide-react";
import type { OwnerUserDetail } from "../types";
import type { UserAction } from "./types";
export function UserActionBar({ detail, can, onAction }: { detail: OwnerUserDetail; can(permission: string): boolean; onAction(action: UserAction): void }) {
  if (detail.is_owner) return <div className="owner-user-owner-lock"><Crown size={17} /> Власника не можна змінювати.</div>;
  return <div className="owner-user-actions">{can("vip.manage") ? <button type="button" onClick={() => onAction("vip")}><Crown size={16} /> VIP</button> : null}{can("users.block") ? <button type="button" onClick={() => onAction("block")}><Ban size={16} /> {detail.is_blocked ? "Розблокувати" : "Блок"}</button> : null}{can("xp.manage") ? <button type="button" onClick={() => onAction("xp")}><Zap size={16} /> XP</button> : null}{can("staff.manage") ? <button type="button" onClick={() => onAction("role")}><UserCog size={16} /> Роль</button> : null}{can("users.notes") ? <button type="button" onClick={() => onAction("note")}><MessageSquareText size={16} /> Нотатка</button> : null}{can("users.notes") ? <button type="button" onClick={() => onAction("tag")}><Tag size={16} /> Тег</button> : null}{can("users.message") ? <button type="button" onClick={() => onAction("message")}><MessageSquareText size={16} /> Написати</button> : null}</div>;
}
"""

USER_ACTION_SHEET = r"""import { useMemo, useState } from "react";
import { X } from "lucide-react";
import { ownerApi } from "../ownerApi";
import type { OwnerUserDetail, StaffRole } from "../types";
import type { UserAction } from "./types";
export function UserActionSheet({ action, detail, saving, onClose, onRun }: { action: Exclude<UserAction, null>; detail: OwnerUserDetail; saving: boolean; onClose(): void; onRun(task: () => Promise<unknown>): void }) {
  const [reason, setReason] = useState(""); const [amount, setAmount] = useState("0"); const [groupId, setGroupId] = useState(""); const [message, setMessage] = useState(""); const [note, setNote] = useState(detail.note); const [tag, setTag] = useState(""); const [role, setRole] = useState<StaffRole>("support"); const [vipMode, setVipMode] = useState<"permanent" | "until">("permanent"); const [vipDate, setVipDate] = useState("");
  const minimumDate = useMemo(() => new Date(Date.now() + 86_400_000).toISOString().slice(0, 10), []);
  const title = action === "vip" ? "Керування VIP" : action === "block" ? "Керування доступом" : action === "xp" ? "Зміна XP" : action === "role" ? "Роль команди" : action === "note" ? "Приватна нотатка" : action === "tag" ? "Новий тег" : "Повідомлення від бота";
  const submit = () => { if (action === "vip") { if (detail.vip.is_active) onRun(() => ownerApi.revokeVip(detail.telegram_id, { reason, confirmation: "ВІДКЛИКАТИ VIP" })); else onRun(() => ownerApi.grantVip(detail.telegram_id, { mode: vipMode, ...(vipMode === "until" && vipDate ? { expires_at: new Date(`${vipDate}T23:59:59Z`).toISOString() } : {}), reason, confirmation: "ВИДАТИ VIP" })); } else if (action === "block") onRun(() => detail.is_blocked ? ownerApi.unblockUser(detail.telegram_id, reason) : ownerApi.blockUser(detail.telegram_id, reason)); else if (action === "xp") onRun(() => ownerApi.adjustXp(detail.telegram_id, Number(amount), reason, groupId ? Number(groupId) : undefined)); else if (action === "role") onRun(() => ownerApi.setRole(detail.telegram_id, role)); else if (action === "note") onRun(() => ownerApi.saveNote(detail.telegram_id, note)); else if (action === "tag") onRun(() => ownerApi.addTag(detail.telegram_id, tag)); else onRun(() => ownerApi.messageUser(detail.telegram_id, message)); };
  return <section className="owner-user-action-sheet"><header><strong>{title}</strong><button type="button" onClick={onClose}><X size={17} /></button></header>{action === "vip" && !detail.vip.is_active ? <div className="owner-action-choice"><button type="button" className={vipMode === "permanent" ? "is-active" : ""} onClick={() => setVipMode("permanent")}>Безстроково</button><button type="button" className={vipMode === "until" ? "is-active" : ""} onClick={() => setVipMode("until")}>До дати</button></div> : null}{action === "vip" && !detail.vip.is_active && vipMode === "until" ? <input type="date" min={minimumDate} value={vipDate} onChange={(event) => setVipDate(event.target.value)} /> : null}{action === "xp" ? <><input type="number" min={-100000} max={100000} value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="Наприклад: 100 або -50" /><select value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Глобальний XP</option>{detail.groups.map((group) => <option key={group.telegram_chat_id} value={group.telegram_chat_id}>{group.title}</option>)}</select></> : null}{action === "role" ? <select value={role} onChange={(event) => setRole(event.target.value as StaffRole)}><option value="support">Support</option><option value="moderator">Moderator</option><option value="admin">Admin</option></select> : null}{action === "note" ? <textarea value={note} maxLength={4000} onChange={(event) => setNote(event.target.value)} placeholder="Внутрішня нотатка для команди" /> : null}{action === "tag" ? <input value={tag} maxLength={32} onChange={(event) => setTag(event.target.value)} placeholder="Наприклад: тестер" /> : null}{action === "message" ? <textarea value={message} maxLength={1000} onChange={(event) => setMessage(event.target.value)} placeholder="Текст приватного повідомлення" /> : null}{(["vip", "block", "xp"] as UserAction[]).includes(action) ? <textarea value={reason} maxLength={500} onChange={(event) => setReason(event.target.value)} placeholder="Обов’язкова причина" /> : null}<div className="owner-user-action-buttons">{action === "role" && detail.role && detail.role !== "owner" ? <button type="button" className="is-danger" disabled={saving || reason.trim().length < 3} onClick={() => onRun(() => ownerApi.removeRole(detail.telegram_id, reason))}>Зняти роль</button> : null}<button type="button" disabled={saving} onClick={submit}>{saving ? "Зберігаю…" : action === "block" ? (detail.is_blocked ? "Розблокувати" : "Повністю заблокувати") : action === "message" ? "Надіслати" : "Підтвердити"}</button></div></section>;
}
"""

OWNER_USER_DRAWER = r"""import { Ban, Crown, ShieldCheck, Zap } from "lucide-react";
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
"""


def split_owner_frontend() -> None:
    write("miniapp/src/owner/hooks/useOwnerWorkspace.ts", OWNER_HOOK)
    write("miniapp/src/owner/OwnerRoutes.tsx", OWNER_ROUTES)
    write("miniapp/src/owner/OwnerApp.tsx", OWNER_APP)
    write("miniapp/src/owner/users/types.ts", USER_TYPES)
    write("miniapp/src/owner/users/UserDrawerHeader.tsx", USER_HEADER)
    write("miniapp/src/owner/users/UserDrawerTabs.tsx", USER_TABS)
    write("miniapp/src/owner/users/UserDrawerContent.tsx", USER_CONTENT)
    write("miniapp/src/owner/users/UserActionBar.tsx", USER_ACTION_BAR)
    write("miniapp/src/owner/users/UserActionSheet.tsx", USER_ACTION_SHEET)
    write("miniapp/src/owner/OwnerUserDrawer.tsx", OWNER_USER_DRAWER)


def move_feature_styles() -> None:
    main_path = ROOT / "miniapp/src/main.tsx"
    main = main_path.read_text(encoding="utf-8")
    main = re.sub(r'import "\./styles/[^"]+\.css";\n', "", main)
    main = main.replace(
        'import { RootRouter } from "./routing/RootRouter";\n',
        'import { RootRouter } from "./routing/RootRouter";\nimport "./styles/global.css";\n',
    )
    main_path.write_text(main, encoding="utf-8")
    write(
        "miniapp/src/styles/app.ts",
        "\n".join(
            f'import "./{name}.css";'
            for name in [
                "bottom-nav-v2",
                "blocked-account",
                "group-settings",
                "groups-v2",
                "group-center",
                "achievement-celebration",
                "achievement-collection",
                "achievement-card-fixes",
                "achievement-showcase-v3",
                "onboarding",
                "profile-experience",
                "year-summary",
            ]
        ),
    )
    write(
        "miniapp/src/owner/styles.ts",
        'import "../styles/owner.css";\nimport "../styles/owner-revenue.css";\nimport "../styles/owner-mobile.css";\nimport "../styles/owner-user-control.css";',
    )
    write(
        "miniapp/src/premium/styles.ts",
        'import "../styles/featured-premium.css";\nimport "../styles/premium.css";\nimport "../styles/premium-identity.css";\nimport "../styles/premium-purchase.css";',
    )
    write("miniapp/src/vip/styles.ts", 'import "../styles/vip.css";')
    app_path = ROOT / "miniapp/src/App.tsx"
    app = app_path.read_text(encoding="utf-8")
    if 'import "./styles/app";' not in app:
        app = app.replace(
            'import { isTelegramContext } from "./telegram/sdk";\n',
            'import { isTelegramContext } from "./telegram/sdk";\nimport "./styles/app";\n',
        )
    app_path.write_text(app, encoding="utf-8")
    for rel, style_import in [
        ("miniapp/src/premium/PremiumContext.tsx", 'import "./styles";\n'),
        ("miniapp/src/vip/VipApp.tsx", 'import "./styles";\n'),
    ]:
        p = ROOT / rel
        text = p.read_text(encoding="utf-8")
        if style_import.strip() not in text:
            text = style_import + text
        p.write_text(text, encoding="utf-8")


def mark_plan_complete() -> None:
    plan = ROOT / "docs/superpowers/plans/2026-07-24-routing-and-structure-refactor.md"
    if plan.exists():
        plan.write_text(
            plan.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8"
        )


def main() -> None:
    split_owner_frontend()
    move_feature_styles()
    split_owner_routes()
    split_user_control_repository()
    mark_plan_complete()


if __name__ == "__main__":
    main()
