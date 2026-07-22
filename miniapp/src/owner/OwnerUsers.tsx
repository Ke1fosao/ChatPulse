import { Crown, Search, ShieldOff, Sparkles, UserRoundCog, X } from "lucide-react";
import { useMemo, useState } from "react";
import type { OwnerUser, VipFilter, VipGrantPayload, VipRevokePayload } from "./types";

interface OwnerUsersProps {
  users: OwnerUser[];
  total: number;
  loading: boolean;
  query: string;
  vipFilter: VipFilter;
  onQueryChange(value: string): void;
  onVipFilterChange(value: VipFilter): void;
  onRefresh(): void;
  onGrant(userId: number, payload: VipGrantPayload): Promise<void>;
  onRevoke(userId: number, payload: VipRevokePayload): Promise<void>;
}

function dateLabel(value: string | null): string {
  if (!value) return "Безстроковий доступ";
  return `до ${new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium" }).format(new Date(value))}`;
}

export function OwnerUsers({
  users,
  total,
  loading,
  query,
  vipFilter,
  onQueryChange,
  onVipFilterChange,
  onRefresh,
  onGrant,
  onRevoke,
}: OwnerUsersProps) {
  const [selected, setSelected] = useState<OwnerUser | null>(null);
  const [mode, setMode] = useState<"permanent" | "until">("permanent");
  const [expiresAt, setExpiresAt] = useState("");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const minimumDate = useMemo(
    () => new Date(Date.now() + 86_400_000).toISOString().slice(0, 10),
    [],
  );

  const close = () => {
    setSelected(null);
    setMode("permanent");
    setExpiresAt("");
    setReason("");
    setFormError("");
  };

  const grant = async () => {
    if (!selected) return;
    if (reason.trim().length < 3) {
      setFormError("Напиши коротку причину видачі VIP.");
      return;
    }
    if (mode === "until" && !expiresAt) {
      setFormError("Вибери дату завершення VIP.");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await onGrant(selected.telegram_id, {
        mode,
        ...(mode === "until"
          ? { expires_at: new Date(`${expiresAt}T23:59:59Z`).toISOString() }
          : {}),
        reason: reason.trim(),
        confirmation: "ВИДАТИ VIP",
      });
      close();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Не вдалося видати VIP.");
    } finally {
      setSaving(false);
    }
  };

  const revoke = async () => {
    if (!selected) return;
    if (reason.trim().length < 3) {
      setFormError("Напиши причину відкликання VIP.");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await onRevoke(selected.telegram_id, {
        reason: reason.trim(),
        confirmation: "ВІДКЛИКАТИ VIP",
      });
      close();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Не вдалося відкликати VIP.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="owner-page">
      <header className="owner-page-heading">
        <div>
          <p>Доступ і підписка</p>
          <h2>Користувачі</h2>
        </div>
        <span className="owner-count">{total}</span>
      </header>

      <section className="owner-toolbar">
        <label className="owner-search">
          <Search size={17} />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Ім’я, username або Telegram ID"
          />
        </label>
        <div className="owner-filter-row">
          {(["all", "active", "inactive"] as VipFilter[]).map((filter) => (
            <button
              key={filter}
              type="button"
              className={vipFilter === filter ? "is-active" : ""}
              onClick={() => onVipFilterChange(filter)}
            >
              {filter === "all" ? "Усі" : filter === "active" ? "VIP" : "Без VIP"}
            </button>
          ))}
          <button type="button" onClick={onRefresh}>Оновити</button>
        </div>
      </section>

      <section className="owner-list" aria-busy={loading}>
        {users.length === 0 ? (
          <div className="owner-empty">
            {loading ? "Завантаження користувачів…" : "Користувачів не знайдено."}
          </div>
        ) : users.map((user) => (
          <article className="owner-user-card" key={user.telegram_id}>
            <div className="owner-user-avatar">
              {user.display_name.slice(0, 2).toUpperCase()}
            </div>
            <div className="owner-user-main">
              <div>
                <strong>{user.display_name}</strong>
                {user.is_vip ? (
                  <span className="vip-badge"><Crown size={11} /> VIP</span>
                ) : null}
              </div>
              <p>{user.username ? `@${user.username}` : `ID ${user.telegram_id}`}</p>
              <small>
                {user.global_xp_total.toLocaleString("uk-UA")} XP · {user.groups_count} груп · {user.is_vip ? dateLabel(user.vip_expires_at) : "Free"}
              </small>
            </div>
            <button
              type="button"
              className="owner-manage-button"
              aria-label={`Керувати VIP для ${user.display_name}`}
              onClick={() => setSelected(user)}
            >
              <UserRoundCog size={18} />
            </button>
          </article>
        ))}
      </section>

      {selected ? (
        <div
          className="owner-modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !saving) close();
          }}
        >
          <section
            className="owner-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Керування VIP"
          >
            <header>
              <div>
                <p>{selected.is_vip ? "Активний VIP" : "Новий VIP-клієнт"}</p>
                <h3>{selected.display_name}</h3>
              </div>
              <button type="button" aria-label="Закрити" disabled={saving} onClick={close}>
                <X size={19} />
              </button>
            </header>

            {!selected.is_vip ? (
              <div className="owner-mode-grid">
                <button
                  type="button"
                  className={mode === "permanent" ? "is-active" : ""}
                  onClick={() => setMode("permanent")}
                >
                  <Crown size={18} /><strong>Безстроково</strong><small>Поки ти не відкличеш</small>
                </button>
                <button
                  type="button"
                  className={mode === "until" ? "is-active" : ""}
                  onClick={() => setMode("until")}
                >
                  <Sparkles size={18} /><strong>До дати</strong><small>Автоматичне завершення</small>
                </button>
              </div>
            ) : (
              <div className="owner-current-vip">
                <Crown size={18} />
                <span>Доступ активний {dateLabel(selected.vip_expires_at)}</span>
              </div>
            )}

            {!selected.is_vip && mode === "until" ? (
              <label className="owner-field">
                <span>VIP діє до</span>
                <input
                  type="date"
                  min={minimumDate}
                  value={expiresAt}
                  onChange={(event) => setExpiresAt(event.target.value)}
                />
              </label>
            ) : null}

            <label className="owner-field">
              <span>Причина</span>
              <textarea
                aria-label="Причина"
                value={reason}
                maxLength={300}
                onChange={(event) => setReason(event.target.value)}
                placeholder={selected.is_vip
                  ? "Чому відкликаєш VIP"
                  : "Наприклад: партнерський клієнт"}
              />
            </label>

            {formError ? <p className="owner-form-error">{formError}</p> : null}

            {selected.is_vip ? (
              <button
                type="button"
                className="owner-danger-action"
                disabled={saving}
                onClick={() => void revoke()}
              >
                <ShieldOff size={18} /> {saving ? "Відкликаю…" : "Відкликати VIP"}
              </button>
            ) : (
              <button
                type="button"
                className="owner-primary-action"
                disabled={saving}
                onClick={() => void grant()}
              >
                <Crown size={18} /> {saving ? "Видаю…" : "Видати VIP"}
              </button>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}
