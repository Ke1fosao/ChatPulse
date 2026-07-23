import { Award, Crown, Sparkles, Target, Trophy } from "lucide-react";
import type { GroupAwardsPayload } from "../../api/groups-v2";
import { AchievementCard } from "../../components/AchievementCard";
import { AchievementIcon } from "../achievements/AchievementVisual";

interface GroupAwardsTabProps {
  data: GroupAwardsPayload;
}

export function GroupAwardsTab({ data }: GroupAwardsTabProps) {
  const earned = data.achievements.filter((item) => item.earned);

  return (
    <div className="group-tab-content group-awards-tab">
      <section className="group-awards-intro">
        <div>
          <p className="eyebrow">Характер групи</p>
          <h2>Нагороди й номінації</h2>
          <p>Тут зібрано те, чим ця група відрізняється від інших.</p>
        </div>
        <span><Trophy size={23} /></span>
      </section>

      {data.highlighted ? (
        <section className={`group-highlighted-achievement is-${data.highlighted.rarity}`}>
          <span><AchievementIcon achievement={data.highlighted} size={29} /></span>
          <div>
            <p className="eyebrow">Особлива нагорода</p>
            <h2>{data.highlighted.title}</h2>
            <small>{data.highlighted.description}</small>
          </div>
          <Crown size={22} />
        </section>
      ) : null}

      <section className="group-overview-section">
        <div className="section-heading">
          <div><p className="eyebrow">Номінації</p><h2>Зірки періоду</h2></div>
          <Award size={21} />
        </div>
        {data.nominations.length ? (
          <div className="group-nominations-grid">
            {data.nominations.map((nomination) => (
              <article key={nomination.metric}>
                <span>{nomination.title.split(" ")[0]}</span>
                <div>
                  <small>{nomination.title}</small>
                  <strong>{nomination.display_name}</strong>
                  <em>{nomination.value.toLocaleString("uk-UA")}</em>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="group-tab-empty">
            <Award size={25} />
            <strong>Номінації ще формуються</strong>
            <span>Потрібно трохи більше активності за вибраний період.</span>
          </div>
        )}
      </section>

      {data.nearest.length ? (
        <section className="group-overview-section">
          <div className="section-heading">
            <div><p className="eyebrow">Наступна ціль</p><h2>Найближчі досягнення</h2></div>
            <Target size={21} />
          </div>
          <div className="achievement-list group-achievement-list">
            {data.nearest.map((achievement) => (
              <AchievementCard achievement={achievement} key={achievement.code} />
            ))}
          </div>
        </section>
      ) : null}

      <section className="group-overview-section">
        <div className="section-heading">
          <div><p className="eyebrow">Колекція групи</p><h2>Отримані нагороди</h2></div>
          <span className="count-pill">{earned.length}</span>
        </div>
        {earned.length ? (
          <div className="achievement-list group-achievement-list">
            {earned.slice(0, 8).map((achievement) => (
              <AchievementCard achievement={achievement} key={achievement.code} />
            ))}
          </div>
        ) : (
          <div className="group-tab-empty">
            <Sparkles size={25} />
            <strong>Перша нагорода попереду</strong>
            <span>Продовжуй брати участь у житті групи.</span>
          </div>
        )}
      </section>
    </div>
  );
}
