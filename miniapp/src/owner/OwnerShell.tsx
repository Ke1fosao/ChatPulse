import {
  Activity,
  ArrowLeft,
  Crown,
  History,
  LayoutDashboard,
  ShieldCheck,
  Users,
  WalletCards,
} from "lucide-react";
import { useMemo, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { appPaths } from "../routing/paths";
import type { OwnerSession, OwnerTab } from "./types";
import { useOwnerViewport } from "./useOwnerViewport";

interface OwnerShellProps {
  session: OwnerSession;
  activeTab: OwnerTab;
  onTabChange(tab: OwnerTab): void;
  children: ReactNode;
  busy?: boolean;
}

const tabs: Array<{ id: OwnerTab; label: string; icon: typeof LayoutDashboard }> = [
  { id: "overview", label: "Огляд", icon: LayoutDashboard },
  { id: "users", label: "Користувачі", icon: Users },
  { id: "groups", label: "Групи", icon: Activity },
  { id: "payments", label: "Оплати", icon: WalletCards },
  { id: "audit", label: "Аудит", icon: History },
];

const roleLabels = {
  owner: "OWNER",
  admin: "ADMIN",
  moderator: "MODERATOR",
  support: "SUPPORT",
} as const;

export function OwnerShell({
  session,
  activeTab,
  onTabChange,
  children,
  busy = false,
}: OwnerShellProps) {
  const navigate = useNavigate();
  useOwnerViewport();
  const availableTabs = useMemo(
    () => session.actor.is_owner ? tabs : tabs.filter((tab) => tab.id === "users"),
    [session.actor.is_owner],
  );
  const RoleIcon = session.actor.is_owner ? Crown : ShieldCheck;

  return (
    <div className="owner-shell">
      <div className="owner-ambient owner-ambient--one" />
      <div className="owner-ambient owner-ambient--two" />
      <header className="owner-topbar">
        <button
          type="button"
          className="owner-icon-button"
          aria-label="Повернутися в ChatPulse"
          onClick={() => navigate(appPaths.home)}
        >
          <ArrowLeft size={19} />
        </button>
        <div className="owner-brand">
          <span><Crown size={20} /></span>
          <div>
            <p>Private system</p>
            <h1>Owner Control</h1>
          </div>
        </div>
        <div className="owner-security-badge">
          <ShieldCheck size={14} />
          <span>{busy ? "SYNC" : "SECURE"}</span>
        </div>
      </header>

      <section className="owner-identity">
        <div className="owner-avatar">
          {session.owner.photo_url ? (
            <img src={session.owner.photo_url} alt="" />
          ) : (
            session.owner.display_name.slice(0, 2).toUpperCase()
          )}
        </div>
        <div>
          <p>{session.actor.is_owner ? "Єдиний власник" : "Команда ChatPulse"}</p>
          <strong>{session.owner.display_name}</strong>
          <small>
            {session.owner.username ? `@${session.owner.username}` : `ID ${session.owner.telegram_id}`}
          </small>
        </div>
        <span className="owner-role-pill"><RoleIcon size={13} /> {roleLabels[session.actor.role]}</span>
      </section>

      <main className="owner-content">{children}</main>

      <nav
        className={`owner-nav${availableTabs.length === 5 ? " owner-nav--five" : " owner-nav--single"}`}
        aria-label="Owner Panel"
      >
        {availableTabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              type="button"
              className={activeTab === tab.id ? "is-active" : ""}
              onClick={() => onTabChange(tab.id)}
            >
              <Icon size={18} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
