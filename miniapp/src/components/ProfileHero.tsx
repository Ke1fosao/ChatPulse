import {
  ArrowUpRight,
  ChevronRight,
  Crown,
  ShieldCheck,
  Sparkles,
  Star,
  UserRound,
} from "lucide-react";
import type { AccountAccess, GlobalProgress, UserSummary } from "../api/types";

interface ProfileHeroProps {
  user: UserSummary;
  account: AccountAccess;
  progress: GlobalProgress;
  onShare?(): void;
  onOpenLevels?(): void;
}

function accountBadge(account: AccountAccess): { label: string; className: string; icon: typeof Crown } {
  if (account.is_owner) return { label: "OWNER · CREATOR", className: "is-owner", icon: Crown };
  if (account.is_vip) return { label: "VIP CLIENT", className: "is-vip", icon: Star };
  return { label: "MEMBER · FREE", className: "is-free", icon: UserRound };
}

export function ProfileHero({ user, account, progress, onShare, onOpenLevels }: ProfileHeroProps) {
  const ratio = Math.min(100, Math.round((progress.progress / Math.max(1, progress.needed)) * 100));
  const badge = accountBadge(account);
  const BadgeIcon = badge.icon;
  const remaining = Math.max(0, progress.needed - progress.progress);

  return (
    <section className="profile-hero profile-hero--structured">
      <div className="profile-hero__glow" />
      <div className="profile-hero__top">
        <div className="profile-avatar">
          {user.photo_url ? (
            <img src={user.photo_url} alt="" />
          ) : (
            <span>{user.display_name.slice(0, 1).toUpperCase()}</span>
          )}
          <i><ShieldCheck size={13} /></i>
        </div>
        <div className="profile-hero__identity">
          <p>Твій ChatPulse</p>
          <h2>{user.display_name}</h2>
          <span>{user.username ? `@${user.username}` : "Telegram профіль"}</span>
        </div>
        {onShare ? (
          <button className="icon-button" type="button" onClick={onShare} aria-label="Поділитися профілем">
            <ArrowUpRight size={20} />
          </button>
        ) : null}
      </div>

      <div className={`profile-role-badge ${badge.className}`}>
        <BadgeIcon size={14} />
        <strong>{badge.label}</strong>
        <span>{account.is_owner ? "Повний доступ" : account.is_vip ? "Premium активний" : "Базовий план"}</span>
      </div>

      <button className="profile-level-card" type="button" onClick={onOpenLevels}>
        <div className="level-orbit__number">
          <small>LEVEL</small>
          <strong>{progress.level}</strong>
        </div>
        <div className="profile-level-card__copy">
          <span><Sparkles size={15} /> {progress.tier}</span>
          <strong>{progress.xp_total.toLocaleString("uk-UA")} XP</strong>
          <small>{remaining.toLocaleString("uk-UA")} XP до наступного рівня</small>
          <div className="hero-progress" aria-label={`Прогрес рівня ${ratio}%`}>
            <span style={{ width: `${ratio}%` }} />
          </div>
          <em>{progress.progress.toLocaleString("uk-UA")} / {progress.needed.toLocaleString("uk-UA")} XP</em>
        </div>
        <span className="profile-level-card__action">
          <ChevronRight size={20} />
          <small>Усі рівні</small>
        </span>
      </button>

      <div className="profile-hero__rank profile-hero__rank--structured">
        <div><span>Глобальне місце</span><strong>#{progress.rank}</strong></div>
        <div><span>Серед усіх</span><strong>Топ {Math.max(1, 100 - progress.percentile + 1)}%</strong></div>
        <div><span>Учасників</span><strong>{progress.total_users}</strong></div>
      </div>
    </section>
  );
}
