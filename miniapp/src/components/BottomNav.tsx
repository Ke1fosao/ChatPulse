import {
  Award,
  BarChart3,
  Home,
  Layers3,
  UserRound,
} from "lucide-react";
import type { TabId } from "../api/types";
import { haptic } from "../telegram/sdk";

const items: Array<{
  id: TabId;
  label: string;
  icon: typeof Home;
}> = [
  { id: "home", label: "Головна", icon: Home },
  { id: "groups", label: "Групи", icon: Layers3 },
  { id: "rankings", label: "Рейтинг", icon: BarChart3 },
  { id: "achievements", label: "Досягнення", icon: Award },
  { id: "profile", label: "Профіль", icon: UserRound },
];

interface BottomNavProps {
  active: TabId;
  onChange(tab: TabId): void;
}

export function BottomNav({ active, onChange }: BottomNavProps) {
  return (
    <nav className="bottom-nav" aria-label="Основна навігація">
      {items.map(({ id, label, icon: Icon }) => (
        <button
          className={`bottom-nav__item ${active === id ? "is-active" : ""}`}
          key={id}
          onClick={() => {
            haptic("light");
            onChange(id);
          }}
          type="button"
          aria-current={active === id ? "page" : undefined}
        >
          <Icon aria-hidden="true" size={20} strokeWidth={2.2} />
          <span>{label}</span>
        </button>
      ))}
    </nav>
  );
}
