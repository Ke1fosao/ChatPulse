import type { CSSProperties } from "react";
import { Award, Home, Layers3, UserRound } from "lucide-react";
import type { TabId } from "../api/types";
import { haptic } from "../telegram/sdk";

const items: Array<{
  id: TabId;
  label: string;
  icon: typeof Home;
}> = [
  { id: "home", label: "Головна", icon: Home },
  { id: "groups", label: "Групи", icon: Layers3 },
  { id: "achievements", label: "Досягнення", icon: Award },
  { id: "profile", label: "Профіль", icon: UserRound },
];

interface BottomNavProps {
  active: TabId;
  onChange(tab: TabId): void;
}

export function BottomNav({ active, onChange }: BottomNavProps) {
  const activeIndex = Math.max(
    0,
    items.findIndex((item) => item.id === active),
  );

  return (
    <div className="bottom-nav-wrap">
      <nav
        className="bottom-nav"
        aria-label="Основна навігація"
        style={{ "--active-index": activeIndex } as CSSProperties}
      >
        <span className="bottom-nav__indicator" aria-hidden="true" />
        {items.map(({ id, label, icon: Icon }) => (
          <button
            className={`bottom-nav__item ${active === id ? "is-active" : ""}`}
            key={id}
            onClick={() => {
              if (active === id) return;
              haptic("light");
              onChange(id);
            }}
            type="button"
            aria-current={active === id ? "page" : undefined}
          >
            <span className="bottom-nav__icon">
              <Icon aria-hidden="true" size={22} strokeWidth={2.15} />
            </span>
            <span className="bottom-nav__label">{label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
