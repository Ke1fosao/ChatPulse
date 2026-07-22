import {
  Activity,
  ArrowLeft,
  Crown,
  History,
  LayoutDashboard,
  ShieldCheck,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";
import type { OwnerSession, OwnerTab } from "./types";

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
  { id: "audit", label: "Аудит", icon: History },
];

export function OwnerShell({
  session,
  activeTab,
  onTabChange,
  children,
  busy = false,
}: OwnerShellProps) {
  return (
    <div className="owner-shell">
      <div className="owner-ambient owner-ambient--one" />
      <div className="owner-ambient owner-ambient--two" />
      <header className="owner-topbar">
        <button
          type="button"
          className="owner-icon-button"
          aria-label="Повернутися в ChatPulse"
          onClick={() => window.location.assign("/miniapp")}
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
          <p>Єдиний власник</p>
          <strong>{session.owner.display_name}</strong>
          <small>
            {session.owner.username ? `@${session.owner.username}` : `ID ${session.owner.telegram_id}`}
          </small>
        </div>
        <span className="owner-role-pill"><Crown size={13} /> OWNER</span>
      </section>

      <main className="owner-content">{children}</main>

      <nav className="owner-nav" aria-label="Owner Panel">
        {tabs.map((tab) => {
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
