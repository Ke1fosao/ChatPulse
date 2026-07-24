import type { DrawerTab } from "./types";
const tabs: Array<[DrawerTab, string]> = [["overview", "Огляд"], ["groups", "Групи"], ["payments", "Платежі"], ["history", "Історія"]];
export function UserDrawerTabs({ active, onChange }: { active: DrawerTab; onChange(tab: DrawerTab): void }) {
  return <nav className="owner-user-tabs" aria-label="Розділи користувача">{tabs.map(([id, label]) => <button key={id} type="button" className={active === id ? "is-active" : ""} onClick={() => onChange(id)}>{label}</button>)}</nav>;
}
