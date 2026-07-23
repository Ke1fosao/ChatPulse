import {
  Ban,
  Crown,
  History,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  Tag,
  UserCog,
  Users,
  X,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { ownerApi } from "./ownerApi";
import type { OwnerUserDetail, StaffRole } from "./types";

interface OwnerUserDrawerProps {
  userId: number | null;
  permissions: string[];
  onClose(): void;
  onChanged(): void | Promise<void>;
}

type DrawerTab = "overview" | "groups" | "payments" | "history";
type Action = "vip" | "block" | "xp" | "role" | "note" | "tag" | "message" | null;

const dateTime = new Intl.DateTimeFormat("uk-UA", {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatDate(value?: string | null): string {
  return value ? dateTime.format(new Date(value)) : "—";
}

export function OwnerUserDrawer({ userId, permissions, onClose, onChanged }: OwnerUserDrawerProps) {
  const [detail, setDetail] = useState<OwnerUserDetail | null>(null);
  const [tab, setTab] = useState<DrawerTab>("overview");
  const [action, setAction] = useState<Action>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [reason, setReason] = useState("");
  const [amount, setAmount] = useState("0");
  const [groupId, setGroupId] = useState("");
  const [message, setMessage] = useState("");
  const [note, setNote] = useState("");
  const [tag, setTag] = useState("");
  const [role, setRole] = useState<StaffRole>("support");
  const [vipMode, setVipMode] = useState<"permanent" | "until">("permanent");
  const [vipDate, setVipDate] = useState("");

  const can = (permission: string) => permissions.includes(permission);
  const minimumDate = useMemo(
    () => new Date(Date.now() + 86_400_000).toISOString().slice(0, 10),
    [],
  );

  const load = async () => {
    if (userId === null) return;
    setLoading(true);
    setError("");
    try {
      const payload = await ownerApi.userDetail(userId);
      setDetail(payload);
      setNote(payload.note);
    } catch (reasonValue) {
      setError(reasonValue instanceof Error ? reasonValue.message : "Не вдалося відкрити користувача.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId === null) return;
    document.body.classList.add("owner-modal-open");
    document.body.style.overflow = "hidden";
    void load();
    return () => {
      document.body.classList.remove("owner-modal-open");
      document.body.style.overflow = "";
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  useEffect(() => {
    if (userId === null) {
      setDetail(null);
      setAction(null);
      setTab("overview");
      setError("");
    }
  }, [userId]);

  const resetForm = () => {
    setAction(null);
    setReason("");
    setAmount("0");
    setGroupId("");
    setMessage("");
    setTag("");
    setVipMode("permanent");
    setVipDate("");
  };

  const run = async (task: () => Promise<unknown>) => {
    setSaving(true);
    setError("");
    try {
      await task();
      await Promise.all([load(), Promise.resolve(onChanged())]);
      resetForm();
    } catch (reasonValue) {
      setError(reasonValue instanceof Error ? reasonValue.message : "Не вдалося зберегти зміну.");
    } finally {
      setSaving(false);
    }
  };

  if (userId === null) return null;

  const drawer = (
    <div className="owner-user-drawer-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !saving) onClose();
    }}>
      <section className="owner-user-drawer" role="dialog" aria-modal="true" aria-label="Картка користувача">
        <header className="owner-user-drawer__header">
          <div className="owner-user-drawer__avatar">
            {detail?.display_name.slice(0, 2).toUpperCase() ?? "…"}
          </div>
          <div>
            <p>{detail?.role ? detail.role.toUpperCase() : "КОРИСТУВАЧ"}</p>
            <h3>{detail?.display_name ?? "Завантаження…"}</h3>
            <small>{detail?.username ? `@${detail.username}` : `ID ${userId}`}</small>
          </div>
          <button type="button" aria-label="Закрити картку" onClick={onClose} disabled={saving}>
            <X size={19} />
          </button>
        </header>

        {loading && !detail ? <div className="owner-empty">Завантаження картки…</div> : null}
        {error ? <button type="button" className="owner-error-banner" onClick={() => setError("")}>{error}</button> : null}

        {detail ? (
          <>
            <div className="owner-user-status-row">
              <span className={detail.is_blocked ? "is-danger" : "is-ok"}>
                {detail.is_blocked ? <Ban size={13} /> : <ShieldCheck size={13} />}
                {detail.is_blocked ? "Заблокований" : "Активний"}
              </span>
              <span className={detail.vip.is_active ? "is-vip" : ""}><Crown size={13} /> {detail.vip.is_active ? "VIP" : "Free"}</span>
              <span><Zap size={13} /> {detail.global_xp_total.toLocaleString("uk-UA")} XP</span>
            </div>

            <nav className="owner-user-tabs" aria-label="Розділи користувача">
              {([
                ["overview", "Огляд"],
                ["groups", "Групи"],
                ["payments", "Платежі"],
                ["history", "Історія"],
              ] as Array<[DrawerTab, string]>).map(([id, label]) => (
                <button key={id} type="button" className={tab === id ? "is-active" : ""} onClick={() => setTab(id)}>{label}</button>
              ))}
            </nav>

            <div className="owner-user-drawer__body">
              {tab === "overview" ? (
                <div className="owner-user-detail-grid">
                  <article><small>Telegram ID</small><strong>{detail.telegram_id}</strong></article>
                  <article><small>Рівень</small><strong>{detail.global_level}</strong></article>
                  <article><small>Реєстрація</small><strong>{formatDate(detail.created_at)}</strong></article>
                  <article><small>Остання активність</small><strong>{formatDate(detail.last_activity_at)}</strong></article>

                  {detail.is_blocked ? (
                    <section className="owner-user-warning">
                      <Ban size={18} />
                      <div><strong>Повний блок</strong><p>{detail.restriction?.reason || "Причину не вказано"}</p></div>
                    </section>
                  ) : null}

                  <section className="owner-user-note-card">
                    <div><MessageSquareText size={16} /><strong>Приватна нотатка</strong></div>
                    <p>{detail.note || "Нотатки ще немає."}</p>
                  </section>

                  <section className="owner-user-tag-card">
                    <div><Tag size={16} /><strong>Теги</strong></div>
                    <div className="owner-user-tags">
                      {detail.tags.length ? detail.tags.map((item) => (
                        <button key={item} type="button" disabled={!can("users.notes") || saving} onClick={() => void run(() => ownerApi.removeTag(detail.telegram_id, item))}>#{item} ×</button>
                      )) : <span>Немає тегів</span>}
                    </div>
                  </section>
                </div>
              ) : null}

              {tab === "groups" ? (
                <div className="owner-user-history-list">
                  {detail.groups.length ? detail.groups.map((group) => (
                    <article key={group.telegram_chat_id}>
                      <Users size={17} />
                      <div><strong>{group.title}</strong><small>{group.xp_total} XP · рівень {group.level}</small></div>
                      <time>{formatDate(group.last_seen_at)}</time>
                    </article>
                  )) : <div className="owner-empty">Користувач поки не входить до груп.</div>}
                </div>
              ) : null}

              {tab === "payments" ? (
                <div className="owner-user-payment-summary">
                  <article><small>Усього Stars</small><strong>{detail.payment_summary.stars_total.toLocaleString("uk-UA")} ⭐</strong></article>
                  <article><small>Успішних оплат</small><strong>{detail.payment_summary.payment_count}</strong></article>
                  <article><small>Остання оплата</small><strong>{formatDate(detail.payment_summary.last_payment_at)}</strong></article>
                  <article><small>Підписка</small><strong>{detail.payment_summary.active_subscription ? "Активна" : "Немає"}</strong></article>
                </div>
              ) : null}

              {tab === "history" ? (
                <div className="owner-user-history-list">
                  {detail.audit.length ? detail.audit.map((item) => (
                    <article key={item.id}>
                      <History size={17} />
                      <div><strong>{item.action}</strong><small>Actor ID {item.actor_telegram_user_id}</small></div>
                      <time>{formatDate(item.created_at)}</time>
                    </article>
                  )) : <div className="owner-empty">Історія змін порожня.</div>}
                </div>
              ) : null}
            </div>

            {!detail.is_owner ? (
              <div className="owner-user-actions">
                {can("vip.manage") ? <button type="button" onClick={() => setAction("vip")}><Crown size={16} /> VIP</button> : null}
                {can("users.block") ? <button type="button" onClick={() => setAction("block")}><Ban size={16} /> {detail.is_blocked ? "Розблокувати" : "Блок"}</button> : null}
                {can("xp.manage") ? <button type="button" onClick={() => setAction("xp")}><Zap size={16} /> XP</button> : null}
                {can("staff.manage") ? <button type="button" onClick={() => setAction("role")}><UserCog size={16} /> Роль</button> : null}
                {can("users.notes") ? <button type="button" onClick={() => setAction("note")}><MessageSquareText size={16} /> Нотатка</button> : null}
                {can("users.notes") ? <button type="button" onClick={() => setAction("tag")}><Tag size={16} /> Тег</button> : null}
                {can("users.message") ? <button type="button" onClick={() => setAction("message")}><MessageSquareText size={16} /> Написати</button> : null}
              </div>
            ) : <div className="owner-user-owner-lock"><Crown size={17} /> Власника не можна змінювати.</div>}

            {action ? (
              <section className="owner-user-action-sheet">
                <header><strong>{action === "vip" ? "Керування VIP" : action === "block" ? "Керування доступом" : action === "xp" ? "Зміна XP" : action === "role" ? "Роль команди" : action === "note" ? "Приватна нотатка" : action === "tag" ? "Новий тег" : "Повідомлення від бота"}</strong><button type="button" onClick={resetForm}><X size={17} /></button></header>

                {action === "vip" && !detail.vip.is_active ? (
                  <div className="owner-action-choice">
                    <button type="button" className={vipMode === "permanent" ? "is-active" : ""} onClick={() => setVipMode("permanent")}>Безстроково</button>
                    <button type="button" className={vipMode === "until" ? "is-active" : ""} onClick={() => setVipMode("until")}>До дати</button>
                  </div>
                ) : null}
                {action === "vip" && !detail.vip.is_active && vipMode === "until" ? <input type="date" min={minimumDate} value={vipDate} onChange={(event) => setVipDate(event.target.value)} /> : null}
                {action === "xp" ? (
                  <>
                    <input type="number" min={-100000} max={100000} value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="Наприклад: 100 або -50" />
                    <select value={groupId} onChange={(event) => setGroupId(event.target.value)}>
                      <option value="">Глобальний XP</option>
                      {detail.groups.map((group) => <option key={group.telegram_chat_id} value={group.telegram_chat_id}>{group.title}</option>)}
                    </select>
                  </>
                ) : null}
                {action === "role" ? <select value={role} onChange={(event) => setRole(event.target.value as StaffRole)}><option value="support">Support</option><option value="moderator">Moderator</option><option value="admin">Admin</option></select> : null}
                {action === "note" ? <textarea value={note} maxLength={4000} onChange={(event) => setNote(event.target.value)} placeholder="Внутрішня нотатка для команди" /> : null}
                {action === "tag" ? <input value={tag} maxLength={32} onChange={(event) => setTag(event.target.value)} placeholder="Наприклад: тестер" /> : null}
                {action === "message" ? <textarea value={message} maxLength={1000} onChange={(event) => setMessage(event.target.value)} placeholder="Текст приватного повідомлення" /> : null}
                {(["vip", "block", "xp"] as Action[]).includes(action) ? <textarea value={reason} maxLength={500} onChange={(event) => setReason(event.target.value)} placeholder="Обов’язкова причина" /> : null}

                <div className="owner-user-action-buttons">
                  {action === "role" && detail.role && detail.role !== "owner" ? <button type="button" className="is-danger" disabled={saving || reason.trim().length < 3} onClick={() => void run(() => ownerApi.removeRole(detail.telegram_id, reason))}>Зняти роль</button> : null}
                  <button type="button" disabled={saving} onClick={() => {
                    if (action === "vip") {
                      if (detail.vip.is_active) void run(() => ownerApi.revokeVip(detail.telegram_id, { reason, confirmation: "ВІДКЛИКАТИ VIP" }));
                      else void run(() => ownerApi.grantVip(detail.telegram_id, { mode: vipMode, ...(vipMode === "until" && vipDate ? { expires_at: new Date(`${vipDate}T23:59:59Z`).toISOString() } : {}), reason, confirmation: "ВИДАТИ VIP" }));
                    } else if (action === "block") {
                      void run(() => detail.is_blocked ? ownerApi.unblockUser(detail.telegram_id, reason) : ownerApi.blockUser(detail.telegram_id, reason));
                    } else if (action === "xp") {
                      void run(() => ownerApi.adjustXp(detail.telegram_id, Number(amount), reason, groupId ? Number(groupId) : undefined));
                    } else if (action === "role") {
                      void run(() => ownerApi.setRole(detail.telegram_id, role));
                    } else if (action === "note") {
                      void run(() => ownerApi.saveNote(detail.telegram_id, note));
                    } else if (action === "tag") {
                      void run(() => ownerApi.addTag(detail.telegram_id, tag));
                    } else if (action === "message") {
                      void run(() => ownerApi.messageUser(detail.telegram_id, message));
                    }
                  }}>
                    {saving ? "Зберігаю…" : action === "block" ? (detail.is_blocked ? "Розблокувати" : "Повністю заблокувати") : action === "message" ? "Надіслати" : "Підтвердити"}
                  </button>
                </div>
              </section>
            ) : null}
          </>
        ) : null}
      </section>
    </div>
  );

  return createPortal(drawer, document.body);
}
