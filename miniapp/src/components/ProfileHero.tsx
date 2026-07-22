import { ArrowUpRight, ShieldCheck, Sparkles } from "lucide-react";
import type { GlobalProgress, UserSummary } from "../api/types";

interface ProfileHeroProps {
  user: UserSummary;
  progress: GlobalProgress;
  onShare?(): void;
}

export function ProfileHero({ user, progress, onShare }: ProfileHeroProps) {
  const ratio = Math.min(100, Math.round((progress.progress / progress.needed) * 100));
  return (
    <section className="profile-hero">
      <div className="profile-hero__glow" />
      <div className="profile-hero__top">
        <div className="profile-avatar">
          {user.photo_url ? (
            <img src={user.photo_url} alt="" />
          ) : (
            <span>{user.display_name.slice(0, 1).toUpperCase()}</span>
          )}
          <i>
            <ShieldCheck size={13} />
          </i>
        </div>
        <div className="profile-hero__identity">
          <p>Твій ChatPulse</p>
          <h2>{user.display_name}</h2>
          <span>{user.username ? `@${user.username}` : "Telegram профіль"}</span>
        </div>
        {onShare ? (
          <button className="icon-button" type="button" onClick={onShare} aria-label="Поділитися">
            <ArrowUpRight size={20} />
          </button>
        ) : null}
      </div>

      <div className="level-orbit">
        <div className="level-orbit__number">
          <small>LEVEL</small>
          <strong>{progress.level}</strong>
        </div>
        <div className="level-orbit__copy">
          <span>
            <Sparkles size={15} /> {progress.tier}
          </span>
          <strong>{progress.xp_total.toLocaleString("uk-UA")} XP</strong>
          <small>
            Ще {Math.max(0, progress.needed - progress.progress).toLocaleString("uk-UA")} XP до
            наступного рівня
          </small>
        </div>
      </div>

      <div className="hero-progress" aria-label={`Прогрес рівня ${ratio}%`}>
        <span style={{ width: `${ratio}%` }} />
      </div>
      <div className="profile-hero__rank">
        <span>Глобальне місце</span>
        <strong>#{progress.rank}</strong>
        <small>Топ {Math.max(1, 100 - progress.percentile + 1)}%</small>
      </div>
    </section>
  );
}
