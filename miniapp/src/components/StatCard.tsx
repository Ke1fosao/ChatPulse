import type { ReactNode } from "react";

interface StatCardProps {
  icon: ReactNode;
  label: string;
  value: string | number;
  hint?: string;
  trend?: number | null;
  accent?: boolean;
}

export function StatCard({
  icon,
  label,
  value,
  hint,
  trend,
  accent = false,
}: StatCardProps) {
  return (
    <article className={`stat-card ${accent ? "stat-card--accent" : ""}`}>
      <div className="stat-card__icon">{icon}</div>
      <div className="stat-card__body">
        <span>{label}</span>
        <strong>{value}</strong>
        {hint ? <small>{hint}</small> : null}
      </div>
      {trend !== undefined && trend !== null ? (
        <span className={`trend ${trend >= 0 ? "trend--up" : "trend--down"}`}>
          {trend >= 0 ? "+" : ""}
          {trend}%
        </span>
      ) : null}
    </article>
  );
}
