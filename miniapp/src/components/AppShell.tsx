import type { ReactNode } from "react";
import { Sparkles } from "lucide-react";
import type { TabId } from "../api/types";
import { BottomNav } from "./BottomNav";

interface AppShellProps {
  activeTab: TabId;
  onTabChange(tab: TabId): void;
  children: ReactNode;
  badge?: string;
}

export function AppShell({
  activeTab,
  onTabChange,
  children,
  badge = "LIVE",
}: AppShellProps) {
  return (
    <div className="app-shell">
      <div className="ambient ambient--one" />
      <div className="ambient ambient--two" />
      <header className="topbar">
        <div className="brand-mark" aria-hidden="true">
          <Sparkles size={19} />
        </div>
        <div>
          <p className="eyebrow">Telegram Analytics</p>
          <h1>ChatPulse</h1>
        </div>
        <span className="live-badge">
          <span />
          {badge}
        </span>
      </header>
      <main className="app-content">{children}</main>
      <BottomNav active={activeTab} onChange={onTabChange} />
    </div>
  );
}
