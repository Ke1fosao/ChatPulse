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
import { usePremium } from "../../premium/PremiumContext";
import { VipBadge } from "../../premium/VipBadge";

interface ProfilePageProps {
  data: HomePayload;
  onShare(): void;
  onOpenLevels(): void;
  onOpenAchievements(): void;
  onOpenGroups(): void;
}

export function ProfilePage({
  data,
  onShare,
  onOpenLevels,
  onOpenAchievements,
  onOpenGroups,
}: ProfilePageProps) {
  const { trialAvailable, openVip } = usePremium();
  const openPlan = () => {
    if (data.account.is_owner) {
      window.location.assign("/miniapp/owner");
      return;
    }
    if (data.account.is_vip) {
      window.location.assign("/miniapp/vip?source=profile");
      return;
    }
    openVip("profile", "premium.all");
  };
  const planTitle = data.account.is_owner
    ? "Відкрити Owner Panel"
    : data.account.is_vip
      ? "Керувати ChatPulse VIP"
      : "Відкрий ChatPulse VIP";

  return (
    <div className="page profile-page">
      <ProfileHero
        user={data.user}
        account={data.account}
        progress={data.global_progress}
        onShare={onShare}
        onOpenLevels={onOpenLevels}
      />

      <button
        type="button"
        aria-label={planTitle}
        onClick={openPlan}
        className={`account-plan-card ${
          data.account.is_owner
            ? "account-plan-card--owner"
            : data.account.is_vip
              ? "account-plan-card--vip"
              : "account-plan-card--free"
        }`}
      >
        <span><Crown size={22} /></span>
        <div>
          <div className="account-plan-card__title">
            <p>{planTitle}</p>
            <VipBadge account={data.account} />
          </div>
          <strong>
            {data.account.is_owner
              ? "Повна аналітика та керування ChatPulse"
              : data.account.is_vip
                ? "Усі premium-функції активні"
                : "Більше аналітики там, де вона потрібна"}
          </strong>
          <small>
            {data.account.is_owner
              ? "Роль захищена Telegram ID та серверною перевіркою"
              : data.account.is_vip
                ? data.account.vip_expires_at
                  ? `VIP діє до ${new Intl.DateTimeFormat("uk-UA", {
                      dateStyle: "medium",
                    }).format(new Date(data.account.vip_expires_at))}`
                  : "Безстроковий VIP-доступ"
                : trialAvailable
                  ? "7 днів за 1 ⭐"
                  : "Натисни, щоб переглянути доступні тарифи"}
          </small>
        </div>
        <ExternalLink size={18} />
      </button>

      <section className="profile-milestones panel">
        <div className="section-heading">
          <div><p className="eyebrow">Особисті рекорди</p><h2>Твій прогрес</h2></div>
          <Trophy size={22} />
        </div>
        <div className="milestone-grid">
          <article><Flame size={20} /><strong>{data.quick_stats.longest_streak}</strong><span>рекорд серії</span></article>
          <article><Layers3 size={20} /><strong>{data.quick_stats.groups_count}</strong><span>активних груп</span></article>
          <article><Award size={20} /><strong>{data.recent_achievements.length}</strong><span>нових нагород</span></article>
          <article><ShieldCheck size={20} /><strong>{data.quick_stats.protection_left}</strong><span>днів захисту</span></article>
        </div>
      </section>

      <section className="profile-actions panel">
        <button type="button" onClick={onOpenLevels}>
          <span><Trophy size={20} /></span>
          <div><strong>Усі рівні ChatPulse</strong><small>50 рівнів, статуси та вимоги XP</small></div>
          <ExternalLink size={18} />
        </button>
        <button type="button" onClick={onShare}>
          <span><Share2 size={20} /></span>
          <div><strong>Поділитися профілем</strong><small>PNG-картка та native Telegram share</small></div>
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
        <div><BellRing size={18} /><span>Важливі рівні, платежі та досягнення приходять у Telegram</span></div>
        <div><Info size={18} /><span>VIP не додає XP і не впливає на чесність рейтингів</span></div>
      </section>
    </div>
  );
}
