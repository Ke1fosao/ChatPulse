import {
  Award,
  BellRing,
  Crown,
  ExternalLink,
  Flame,
  Info,
  Layers3,
  LockKeyhole,
  Share2,
  ShieldCheck,
  Trophy,
} from "lucide-react";
import type { HomePayload } from "../../api/types";
import { ProfileHero } from "../../components/ProfileHero";

interface ProfilePageProps {
  data: HomePayload;
  onShare(): void;
  onOpenAchievements(): void;
  onOpenGroups(): void;
}

export function ProfilePage({
  data,
  onShare,
  onOpenAchievements,
  onOpenGroups,
}: ProfilePageProps) {
  return (
    <div className="page profile-page">
      <ProfileHero user={data.user} progress={data.global_progress} onShare={onShare} />

      {data.account.is_owner || data.account.is_vip ? (
        <section className={`account-plan-card ${data.account.is_owner ? "account-plan-card--owner" : "account-plan-card--vip"}`}>
          <span><Crown size={22} /></span>
          <div>
            <p>{data.account.is_owner ? "Owner Access" : "VIP-клієнт"}</p>
            <strong>{data.account.is_owner ? "Повний контроль ChatPulse" : "Усі premium-функції активні"}</strong>
            <small>
              {data.account.is_owner
                ? "Захищено Telegram ID та серверною перевіркою"
                : data.account.vip_expires_at
                  ? `Діє до ${new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium" }).format(new Date(data.account.vip_expires_at))}`
                  : "Безстроковий VIP-доступ"}
            </small>
          </div>
        </section>
      ) : null}

      <section className="profile-milestones panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Особисті рекорди</p>
            <h2>Твій прогрес</h2>
          </div>
          <Trophy size={22} />
        </div>
        <div className="milestone-grid">
          <article>
            <Flame size={20} />
            <strong>{data.quick_stats.longest_streak}</strong>
            <span>рекорд серії</span>
          </article>
          <article>
            <Layers3 size={20} />
            <strong>{data.quick_stats.groups_count}</strong>
            <span>активних груп</span>
          </article>
          <article>
            <Award size={20} />
            <strong>{data.recent_achievements.length}</strong>
            <span>нових нагород</span>
          </article>
          <article>
            <ShieldCheck size={20} />
            <strong>{data.quick_stats.protection_left}</strong>
            <span>днів захисту</span>
          </article>
        </div>
      </section>

      <section className="profile-actions panel">
        {data.account.is_owner ? (
          <button type="button" className="profile-owner-action" onClick={() => window.location.assign("/miniapp/owner")}>
            <span><Crown size={20} /></span>
            <div><strong>Owner Panel</strong><small>Користувачі, VIP, групи та аудит</small></div>
            <ExternalLink size={18} />
          </button>
        ) : null}
        <button type="button" onClick={onShare}>
          <span><Share2 size={20} /></span>
          <div><strong>Поділитися профілем</strong><small>Створи преміальну PNG-картку</small></div>
          <ExternalLink size={18} />
        </button>
        <button type="button" onClick={onOpenAchievements}>
          <span><Award size={20} /></span>
          <div><strong>Мої досягнення</strong><small>Колекція нагород і прогрес</small></div>
          <ExternalLink size={18} />
        </button>
        <button type="button" onClick={onOpenGroups}>
          <span><Layers3 size={20} /></span>
          <div><strong>Мої групи</strong><small>Уся групова статистика</small></div>
          <ExternalLink size={18} />
        </button>
      </section>

      <section className="privacy-card">
        <span><LockKeyhole size={22} /></span>
        <div>
          <strong>Privacy-first аналітика</strong>
          <p>ChatPulse не зберігає тексти повідомлень, підписи або файли — лише безпечні агрегати та технічні ID.</p>
        </div>
      </section>

      <section className="profile-info-list panel">
        <div><BellRing size={18} /><span>Важливі рівні й досягнення приходять у Telegram</span></div>
        <div><Info size={18} /><span>Глобальний рейтинг показує лише твою позицію та percentile</span></div>
      </section>
    </div>
  );
}
