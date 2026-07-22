import { CalendarClock, Crown, ShieldCheck, Sparkles, Star, UserRound } from "lucide-react";
import type { AccountAccess } from "../../api/types";
import { getProfileStatus } from "./profileStatus";

interface AccountStatusCardProps {
  account: AccountAccess;
}

export function AccountStatusCard({ account }: AccountStatusCardProps) {
  const status = getProfileStatus(account);
  const RoleIcon = status.tone === "owner" ? Crown : status.tone === "vip" ? Star : UserRound;

  return (
    <section className={`account-status-card account-status-card--${status.tone}`}>
      <header>
        <div>
          <p className="eyebrow">Права та підписка</p>
          <h2>Статус профілю</h2>
        </div>
        <span><ShieldCheck size={20} /></span>
      </header>

      <div className="account-status-grid">
        <article>
          <span><RoleIcon size={18} /></span>
          <small>Роль</small>
          <strong>{status.role}</strong>
        </article>
        <article>
          <span><Sparkles size={18} /></span>
          <small>Підписка</small>
          <strong>{status.plan}</strong>
        </article>
        <article>
          <span><CalendarClock size={18} /></span>
          <small>Доступ</small>
          <strong>{status.access}</strong>
        </article>
      </div>

      <p className="account-status-card__description">{status.description}</p>
    </section>
  );
}
