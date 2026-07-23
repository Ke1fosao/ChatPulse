import {
  Ban,
  Crown,
  RefreshCw,
  Search,
  ShieldCheck,
  Star,
  UserRoundCog,
  UsersRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { OwnerBulkBar } from "./OwnerBulkBar";
import { OwnerUserDrawer } from "./OwnerUserDrawer";
import type {
  OwnerUser,
  OwnerUserFilters,
  UserPaymentFilter,
  UserRoleFilter,
  UserSort,
  UserStatusFilter,
  VipFilter,
} from "./types";

interface OwnerUsersProps {
  users: OwnerUser[];
  total: number;
  loading: boolean;
  filters: OwnerUserFilters;
  permissions: string[];
  onFiltersChange(filters: OwnerUserFilters): void;
  onRefresh(): void | Promise<void>;
}

const dateFormatter = new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium" });

function dateLabel(value: string | null): string {
  if (!value) return "Безстроково";
  return `до ${dateFormatter.format(new Date(value))}`;
}

function activityLabel(value: string): string {
  const milliseconds = Date.now() - new Date(value).getTime();
  const days = Math.max(0, Math.floor(milliseconds / 86_400_000));
  if (days === 0) return "активний сьогодні";
  if (days === 1) return "активний учора";
  return `активний ${days} дн. тому`;
}

export function OwnerUsers({
  users,
  total,
  loading,
  filters,
  permissions,
  onFiltersChange,
  onRefresh,
}: OwnerUsersProps) {
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const selectableUsers = useMemo(() => users.filter((user) => user.role !== "owner"), [users]);
  const allVisibleSelected = selectableUsers.length > 0
    && selectableUsers.every((user) => selectedSet.has(user.telegram_id));

  useEffect(() => {
    const visibleIds = new Set(users.map((user) => user.telegram_id));
    setSelectedIds((current) => current.filter((id) => visibleIds.has(id)));
  }, [users]);

  const patchFilters = (values: Partial<OwnerUserFilters>) => {
    onFiltersChange({ ...filters, ...values, offset: values.offset ?? 0 });
  };

  const toggleUser = (user: OwnerUser) => {
    if (user.role === "owner") return;
    setSelectedIds((current) => {
      if (current.includes(user.telegram_id)) {
        return current.filter((id) => id !== user.telegram_id);
      }
      if (current.length >= 100) return current;
      return [...current, user.telegram_id];
    });
  };

  const toggleVisible = () => {
    if (allVisibleSelected) {
      const visible = new Set(selectableUsers.map((user) => user.telegram_id));
      setSelectedIds((current) => current.filter((id) => !visible.has(id)));
      return;
    }
    setSelectedIds((current) => {
      const next = new Set(current);
      for (const user of selectableUsers) {
        if (next.size >= 100) break;
        next.add(user.telegram_id);
      }
      return [...next];
    });
  };

  return (
    <>
      <div className="owner-page owner-users-page">
        <header className="owner-page-heading">
          <div>
            <p>Доступ, ролі та активність</p>
            <h2>Користувачі</h2>
          </div>
          <span className="owner-count">{total}</span>
        </header>

        <section className="owner-toolbar owner-user-toolbar">
          <label className="owner-search">
            <Search size={17} />
            <input
              value={filters.query}
              onChange={(event) => patchFilters({ query: event.target.value })}
              placeholder="Ім’я, username або Telegram ID"
            />
          </label>

          <div className="owner-filter-row owner-filter-row--vip">
            {(["all", "active", "inactive", "expiring"] as VipFilter[]).map((filter) => (
              <button
                key={filter}
                type="button"
                className={filters.vip === filter ? "is-active" : ""}
                onClick={() => patchFilters({ vip: filter })}
              >
                {filter === "all"
                  ? "Усі"
                  : filter === "active"
                    ? "VIP"
                    : filter === "inactive"
                      ? "Без VIP"
                      : "VIP завершується"}
              </button>
            ))}
          </div>

          <div className="owner-user-filter-grid">
            <label>
              <span>Статус</span>
              <select
                value={filters.status}
                onChange={(event) => patchFilters({ status: event.target.value as UserStatusFilter })}
              >
                <option value="all">Усі статуси</option>
                <option value="active">Активні</option>
                <option value="inactive">Неактивні 30+ днів</option>
                <option value="blocked">Заблоковані</option>
              </select>
            </label>
            <label>
              <span>Роль</span>
              <select
                value={filters.role}
                onChange={(event) => patchFilters({ role: event.target.value as UserRoleFilter })}
              >
                <option value="all">Усі ролі</option>
                <option value="owner">Owner</option>
                <option value="admin">Admin</option>
                <option value="moderator">Moderator</option>
                <option value="support">Support</option>
                <option value="none">Без ролі</option>
              </select>
            </label>
            <label>
              <span>Оплати</span>
              <select
                value={filters.payment}
                onChange={(event) => patchFilters({ payment: event.target.value as UserPaymentFilter })}
              >
                <option value="all">Усі користувачі</option>
                <option value="paid">Є оплати</option>
                <option value="never">Не платили</option>
              </select>
            </label>
            <label>
              <span>Сортування</span>
              <select
                value={filters.sort}
                onChange={(event) => patchFilters({ sort: event.target.value as UserSort })}
              >
                <option value="activity_desc">Нещодавно активні</option>
                <option value="activity_asc">Давно неактивні</option>
                <option value="created_desc">Нові реєстрації</option>
                <option value="created_asc">Старі реєстрації</option>
                <option value="xp_desc">Найбільше XP</option>
                <option value="xp_asc">Найменше XP</option>
                <option value="groups_desc">Найбільше груп</option>
                <option value="groups_asc">Найменше груп</option>
                <option value="stars_desc">Найбільше Stars</option>
                <option value="stars_asc">Найменше Stars</option>
                <option value="vip_expiry_asc">VIP завершується раніше</option>
              </select>
            </label>
          </div>

          <div className="owner-user-toolbar__footer">
            <label className="owner-user-tag-filter">
              <span>#</span>
              <input
                value={filters.tag}
                maxLength={32}
                onChange={(event) => patchFilters({ tag: event.target.value })}
                placeholder="Фільтр за тегом"
              />
            </label>
            <button type="button" className="owner-text-button" onClick={() => void onRefresh()}>
              <RefreshCw size={15} className={loading ? "is-spinning" : ""} /> Оновити
            </button>
          </div>
        </section>

        {selectableUsers.length ? (
          <section className="owner-selection-row">
            <label>
              <input type="checkbox" checked={allVisibleSelected} onChange={toggleVisible} />
              <span>{allVisibleSelected ? "Зняти вибір" : "Вибрати видимих"}</span>
            </label>
            <small>{selectedIds.length}/100 вибрано</small>
          </section>
        ) : null}

        <section className="owner-list" aria-busy={loading}>
          {users.length === 0 ? (
            <div className="owner-empty">
              {loading ? "Завантаження користувачів…" : "Користувачів за цими фільтрами не знайдено."}
            </div>
          ) : users.map((user) => (
            <article
              className={`owner-user-card owner-user-card--advanced${user.is_blocked ? " is-blocked" : ""}${selectedSet.has(user.telegram_id) ? " is-selected" : ""}`}
              key={user.telegram_id}
            >
              <label className="owner-user-select" aria-label={`Вибрати ${user.display_name}`}>
                <input
                  type="checkbox"
                  checked={selectedSet.has(user.telegram_id)}
                  disabled={user.role === "owner"}
                  onChange={() => toggleUser(user)}
                />
              </label>
              <div className="owner-user-avatar">
                {user.display_name.slice(0, 2).toUpperCase()}
              </div>
              <div className="owner-user-main">
                <div>
                  <strong>{user.display_name}</strong>
                  {user.is_vip ? <span className="vip-badge"><Crown size={11} /> VIP</span> : null}
                  {user.is_blocked ? <span className="owner-user-badge is-danger"><Ban size={11} /> BLOCK</span> : null}
                  {user.role ? <span className="owner-user-badge is-role"><ShieldCheck size={11} /> {user.role.toUpperCase()}</span> : null}
                </div>
                <p>{user.username ? `@${user.username}` : `ID ${user.telegram_id}`}</p>
                <small>
                  {user.global_xp_total.toLocaleString("uk-UA")} XP · {user.groups_count} груп · {activityLabel(user.last_activity_at)}
                </small>
                <div className="owner-user-microstats">
                  <span><Star size={11} /> {user.stars_total.toLocaleString("uk-UA")} Stars</span>
                  <span><UsersRound size={11} /> {user.payment_count} оплат</span>
                  <span><Crown size={11} /> {user.is_vip ? dateLabel(user.vip_expires_at) : "Free"}</span>
                </div>
              </div>
              <button
                type="button"
                className="owner-manage-button"
                aria-label={`Відкрити картку ${user.display_name}`}
                onClick={() => setSelectedUserId(user.telegram_id)}
              >
                <UserRoundCog size={18} />
              </button>
            </article>
          ))}
        </section>

        {total > filters.limit ? (
          <div className="owner-pagination">
            <button
              type="button"
              disabled={filters.offset === 0 || loading}
              onClick={() => patchFilters({ offset: Math.max(0, filters.offset - filters.limit) })}
            >
              Назад
            </button>
            <span>{Math.floor(filters.offset / filters.limit) + 1} / {Math.ceil(total / filters.limit)}</span>
            <button
              type="button"
              disabled={filters.offset + filters.limit >= total || loading}
              onClick={() => patchFilters({ offset: filters.offset + filters.limit })}
            >
              Далі
            </button>
          </div>
        ) : null}
      </div>

      <OwnerUserDrawer
        userId={selectedUserId}
        permissions={permissions}
        onClose={() => setSelectedUserId(null)}
        onChanged={onRefresh}
      />
      <OwnerBulkBar
        selectedIds={selectedIds}
        permissions={permissions}
        onClear={() => setSelectedIds([])}
        onChanged={onRefresh}
      />
    </>
  );
}
