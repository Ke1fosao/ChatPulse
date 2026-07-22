import {
  Award,
  ChevronRight,
  Flame,
  MessageCircleMore,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";
import type { GroupCardData, HomePayload } from "../../api/types";
import { ActivityChart } from "../../components/ActivityChart";
import { GroupCard } from "../../components/GroupCard";
import { ProfileHero } from "../../components/ProfileHero";
import { StatCard } from "../../components/StatCard";

interface HomePageProps {
  data: HomePayload;
  onOpenGroup(group: GroupCardData): void;
  onOpenAchievements(): void;
  onShareProfile(): void;
}

export function HomePage({
  data,
  onOpenGroup,
  onOpenAchievements,
  onShareProfile,
}: HomePageProps) {
  return (
    <div className="page page--home">
      <ProfileHero
        user={data.user}
        account={data.account}
        progress={data.global_progress}
        levelCatalog={data.level_catalog}
        onShare={onShareProfile}
      />

      <section className="stats-grid stats-grid--home">
        <StatCard
          accent
          icon={<Zap size={19} />}
          label="XP сьогодні"
          value={data.quick_stats.xp_today}
          hint="глобальний прогрес"
        />
        <StatCard
          icon={<Flame size={19} />}
          label="Серія"
          value={`${data.quick_stats.current_streak} дн.`}
          hint={`Рекорд: ${data.quick_stats.longest_streak}`}
        />
        <StatCard
          icon={<Shield size={19} />}
          label="Захист"
          value={data.quick_stats.protection_left}
          hint="днів цього місяця"
        />
        <StatCard
          icon={<MessageCircleMore size={19} />}
          label="Повідомлень"
          value={data.quick_stats.messages_7d}
          hint="за 7 днів"
        />
      </section>

      <ActivityChart data={data.activity_series} metric="xp" title="Пульс твого XP" />

      <section className="section-block">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Твій простір</p>
            <h2>Найактивніші групи</h2>
          </div>
          <span className="count-pill">{data.quick_stats.groups_count}</span>
        </div>
        <div className="stack">
          {data.groups.length > 0 ? (
            data.groups.map((group) => (
              <GroupCard group={group} key={group.telegram_chat_id} onOpen={onOpenGroup} />
            ))
          ) : (
            <div className="empty-inline">Додай ChatPulse до групи, щоб побачити аналітику</div>
          )}
        </div>
      </section>

      <section className="section-block">
        <button className="section-heading section-heading--button" type="button" onClick={onOpenAchievements}>
          <div>
            <p className="eyebrow">Колекція</p>
            <h2>Останні досягнення</h2>
          </div>
          <ChevronRight size={20} />
        </button>
        <div className="recent-achievements">
          {data.recent_achievements.length > 0 ? (
            data.recent_achievements.map((achievement) => (
              <article className={`mini-achievement mini-achievement--${achievement.rarity}`} key={achievement.code}>
                <span>{achievement.rarity === "epic" ? <Sparkles /> : <Award />}</span>
                <div>
                  <strong>{achievement.title}</strong>
                  <small>{achievement.group_title}</small>
                </div>
              </article>
            ))
          ) : (
            <div className="empty-inline">Твоє перше досягнення вже близько</div>
          )}
        </div>
      </section>
    </div>
  );
}
