import { Crown, History, Radio, ShieldCheck } from "lucide-react";
import type { OwnerAuditEntry } from "./types";

interface OwnerAuditProps {
  items: OwnerAuditEntry[];
  loading: boolean;
  onRefresh(): void;
}

const actionLabels: Record<string, string> = {
  "vip.granted": "VIP видано",
  "vip.revoked": "VIP відкликано",
  "group.updated": "Групу оновлено",
};

export function OwnerAudit({ items, loading, onRefresh }: OwnerAuditProps) {
  return (
    <div className="owner-page">
      <header className="owner-page-heading">
        <div>
          <p>Append-only history</p>
          <h2>Журнал аудиту</h2>
        </div>
        <button type="button" className="owner-text-button" onClick={onRefresh}>Оновити</button>
      </header>

      <section className="owner-panel owner-audit-notice">
        <ShieldCheck size={20} />
        <p>Тут фіксуються всі зміни VIP і системні дії власника. Секрети та тексти повідомлень у журнал не потрапляють.</p>
      </section>

      <section className="owner-timeline" aria-busy={loading}>
        {items.length === 0 ? (
          <div className="owner-empty">{loading ? "Завантаження аудиту…" : "Керувальних дій ще не було."}</div>
        ) : items.map((item) => {
          const Icon = item.target_type === "group" ? Radio : Crown;
          return (
            <article key={item.id}>
              <span><Icon size={17} /></span>
              <div>
                <div><strong>{actionLabels[item.action] ?? item.action}</strong><em>{item.target_type} · {item.target_id}</em></div>
                <p>{new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.created_at))}</p>
                {typeof item.metadata.reason === "string" ? <small>{item.metadata.reason}</small> : null}
              </div>
              <History size={15} />
            </article>
          );
        })}
      </section>
    </div>
  );
}
