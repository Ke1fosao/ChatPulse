import { Inbox, RefreshCw } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?(): void;
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <section className="empty-state">
      <span className="empty-state__icon">
        <Inbox size={28} />
      </span>
      <h2>{title}</h2>
      <p>{description}</p>
      {actionLabel && onAction ? (
        <button className="secondary-button" type="button" onClick={onAction}>
          <RefreshCw size={17} />
          {actionLabel}
        </button>
      ) : null}
    </section>
  );
}
