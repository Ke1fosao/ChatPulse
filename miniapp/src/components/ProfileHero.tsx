import {
  ArrowUpRight,
  ChevronRight,
  Crown,
  ShieldCheck,
  Sparkles,
  Star,
  Trophy,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import type {
  AccountAccess,
  GlobalProgress,
  LevelCatalog,
  UserSummary,
} from "../api/types";
import { LevelGuideDialog } from "../features/profile/LevelGuideDialog";
import { getProfileStatus } from "../features/profile/profileStatus";

interface ProfileHeroProps {
  user: UserSummary;
  account: AccountAccess;
  progress: GlobalProgress;
  levelCatalog: LevelCatalog;
  onShare?(): void;
}

export function ProfileHero({
  user,
  account,
  progress,
  levelCatalog,
  onShare,
}: ProfileHeroProps) {
  const [levelsOpen, setLevelsOpen] = useState(false);
  const status = getProfileStatus(account);
  const ratio = progress.needed <= 0
    ? 100
    : Math.min(100, Math.round((progress.progress / progress.needed) * 100));
  const remaining = Math.max(0, progress.needed - progress.progress);

  const StatusIcon = status.tone === "owner"
    ? Crown
    : status.tone === "vip"
      ? Star
      : UserRound;

  return (
    <>
      <section className={`profile-hero profile-hero--v2 profile-hero--${status.tone}`}>
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
            <button className="icon-button" type="button" onClick={onShare} aria-label="Поділитися">
              <ArrowUpRight size={20} />
            </button>
          ) : null}
        </div>

        <div className="profile-status-badges" aria-label="Статус акаунта">
          <span className={`profile-status-badge profile-status-badge--${status.tone}`}>
            <StatusIcon size={13} /> {status.role}
          </span>
          <span className="profile-status-badge profile-status-badge--plan">
            <Sparkles size={13} /> {status.plan}
          </span>
          <small>{status.access}</small>
        </div>

        <button
          type="button"
          className="profile-level-card"
          aria-label="Відкрити каталог рівнів"
          onClick={() => setLevelsOpen(true)}
        >
          <div className="profile-level-card__orb">
            <small>LEVEL</small>
            <strong>{progress.level}</strong>
            <span>із {levelCatalog.max_level}</span>
          </div>
          <div className="profile-level-card__copy">
            <span><Sparkles size={15} /> {progress.tier}</span>
            <strong>{progress.xp_total.toLocaleString("uk-UA")} XP</strong>
            <small>
              {progress.needed <= 0
                ? "Максимальний рівень досягнуто"
                : `Ще ${remaining.toLocaleString("uk-UA")} XP до рівня ${progress.level + 1}`}
            </small>
            <div className="hero-progress" aria-label={`Прогрес рівня ${ratio}%`}>
              <span style={{ width: `${ratio}%` }} />
            </div>
          </div>
          <div className="profile-level-card__action">
            <span>Усі рівні</span>
            <ChevronRight size={18} />
          </div>
        </button>

        <div className="profile-hero__summary">
          <article>
            <Trophy size={16} />
            <span>Глобальне місце</span>
            <strong>#{progress.rank}</strong>
          </article>
          <article>
            <Star size={16} />
            <span>Серед учасників</span>
            <strong>Топ {Math.max(1, 100 - progress.percentile + 1)}%</strong>
          </article>
          <article>
            <Crown size={16} />
            <span>Фінальний статус</span>
            <strong>Легенда</strong>
          </article>
        </div>
      </section>

      <LevelGuideDialog
        open={levelsOpen}
        progress={progress}
        catalog={levelCatalog}
        onClose={() => setLevelsOpen(false)}
      />
    </>
  );
}
