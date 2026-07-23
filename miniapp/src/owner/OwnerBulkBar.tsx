import { Ban, Crown, MessageSquareText, Tag, X } from "lucide-react";
import { useMemo, useState } from "react";
import { ownerApi } from "./ownerApi";
import type { BulkAction, BulkActionResult } from "./types";

interface OwnerBulkBarProps {
  selectedIds: number[];
  permissions: string[];
  onClear(): void;
  onChanged(): void | Promise<void>;
}

export function OwnerBulkBar({ selectedIds, permissions, onClear, onChanged }: OwnerBulkBarProps) {
  const [open, setOpen] = useState(false);
  const [action, setAction] = useState<BulkAction>("add_tag");
  const [reason, setReason] = useState("");
  const [tag, setTag] = useState("");
  const [message, setMessage] = useState("");
  const [mode, setMode] = useState<"permanent" | "until">("permanent");
  const [expiresAt, setExpiresAt] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<BulkActionResult | null>(null);

  const actions = useMemo(() => {
    const available: Array<{ id: BulkAction; label: string }> = [];
    if (permissions.includes("bulk.vip")) {
      available.push({ id: "grant_vip", label: "Видати VIP" }, { id: "revoke_vip", label: "Забрати VIP" });
    }
    if (permissions.includes("bulk.block")) {
      available.push({ id: "block", label: "Заблокувати" }, { id: "unblock", label: "Розблокувати" });
    }
    if (permissions.includes("bulk.tag_message")) {
      available.push({ id: "add_tag", label: "Додати тег" }, { id: "remove_tag", label: "Зняти тег" }, { id: "message", label: "Надіслати повідомлення" });
    }
    return available;
  }, [permissions]);

  if (!selectedIds.length || !actions.length) return null;

  const run = async () => {
    setSaving(true);
    setError("");
    setResult(null);
    try {
      const payload = await ownerApi.bulkUsers({
        action,
        user_ids: selectedIds,
        ...(reason.trim() ? { reason: reason.trim() } : {}),
        ...(action === "grant_vip" ? {
          mode,
          ...(mode === "until" && expiresAt
            ? { expires_at: new Date(`${expiresAt}T23:59:59Z`).toISOString() }
            : {}),
        } : {}),
        ...((action === "add_tag" || action === "remove_tag") ? { tag: tag.trim() } : {}),
        ...(action === "message" ? { message_text: message.trim() } : {}),
      });
      setResult(payload);
      await Promise.resolve(onChanged());
      if (!payload.failed.length) {
        window.setTimeout(() => {
          setOpen(false);
          onClear();
        }, 650);
      }
    } catch (reasonValue) {
      setError(reasonValue instanceof Error ? reasonValue.message : "Не вдалося виконати масову дію.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="owner-bulk-bar">
        <strong>{selectedIds.length} вибрано</strong>
        <button type="button" onClick={() => setOpen(true)}>Масова дія</button>
        <button type="button" aria-label="Очистити вибір" onClick={onClear}><X size={17} /></button>
      </div>

      {open ? (
        <div className="owner-bulk-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget && !saving) setOpen(false);
        }}>
          <section className="owner-bulk-modal" role="dialog" aria-modal="true" aria-label="Масова дія">
            <header>
              <div><p>Вибрано користувачів</p><h3>{selectedIds.length}</h3></div>
              <button type="button" aria-label="Закрити масову дію" onClick={() => setOpen(false)}><X size={18} /></button>
            </header>

            <div className="owner-bulk-actions">
              {actions.map((item) => (
                <button key={item.id} type="button" className={action === item.id ? "is-active" : ""} onClick={() => setAction(item.id)}>
                  {item.id.includes("vip") ? <Crown size={15} /> : item.id.includes("block") ? <Ban size={15} /> : item.id.includes("tag") ? <Tag size={15} /> : <MessageSquareText size={15} />}
                  {item.label}
                </button>
              ))}
            </div>

            {action === "grant_vip" ? (
              <div className="owner-action-choice">
                <button type="button" className={mode === "permanent" ? "is-active" : ""} onClick={() => setMode("permanent")}>Безстроково</button>
                <button type="button" className={mode === "until" ? "is-active" : ""} onClick={() => setMode("until")}>До дати</button>
              </div>
            ) : null}
            {action === "grant_vip" && mode === "until" ? <input type="date" value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)} /> : null}
            {(action === "add_tag" || action === "remove_tag") ? <input value={tag} maxLength={32} onChange={(event) => setTag(event.target.value)} placeholder="Назва тегу" /> : null}
            {action === "message" ? <textarea value={message} maxLength={1000} onChange={(event) => setMessage(event.target.value)} placeholder="Текст повідомлення" /> : null}
            {(["grant_vip", "revoke_vip", "block", "unblock"] as BulkAction[]).includes(action) ? <textarea value={reason} maxLength={500} onChange={(event) => setReason(event.target.value)} placeholder="Причина масової дії" /> : null}

            {error ? <p className="owner-form-error">{error}</p> : null}
            {result ? <p className={result.failed.length ? "owner-bulk-result is-partial" : "owner-bulk-result"}>Успішно: {result.succeeded.length}. Помилок: {result.failed.length}.</p> : null}

            <button type="button" className="owner-primary-action" disabled={saving || (action === "message" && selectedIds.length > 50)} onClick={() => void run()}>
              {saving ? "Виконую…" : `Підтвердити для ${selectedIds.length}`}
            </button>
          </section>
        </div>
      ) : null}
    </>
  );
}
