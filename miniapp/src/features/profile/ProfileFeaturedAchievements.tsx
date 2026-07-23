import { Award, RefreshCw, Settings2 } from "lucide-react";
import { useEffect, useState } from "react";
import type { FeaturedAchievement } from "../../vip/types";
import { vipApi } from "../../vip/vipApi";
import { AchievementIcon, rarityLabel } from "../achievements/AchievementVisual";

interface ProfileFeaturedAchievementsProps {
  onConfigure(): void;
}

export function ProfileFeaturedAchievements({
  onConfigure,
}: ProfileFeaturedAchievementsProps) {
  const [items, setItems] = useState<FeaturedAchievement[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    setLoading(true);
    setFailed(false);
    void vipApi
      .featured()
      .then(setItems)
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, [reloadKey]);

  return (
    <section className="profile-featured panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Твоя колекція</p>
          <h2>Вітрина нагород</h2>
        </div>
        <Award size={22} />
      </div>

      {loading ? (
        <div className="profile-featured__loading">
          <RefreshCw className="spin" size={20} /> Завантажуємо нагороди…
        </div>
      ) : failed ? (
        <div className="profile-featured__empty">
          <strong>Не вдалося завантажити вітрину</strong>
          <p>Профіль працює далі. Спробуй оновити лише цей блок.</p>
          <button type="button" onClick={() => setReloadKey((value) => value + 1)}>
            <RefreshCw size={17} /> Повторити
          </button>
        </div>
      ) : items.length ? (
        <>
          <div className="profile-featured__grid">
            {items.map((item, index) => (
              <article
                className={`profile-featured__item profile-featured__item--${item.rarity} ${
                  index < 3 ? "is-primary" : "is-secondary"
                }`}
                key={`${item.code}:${item.scope_key}`}
              >
                <span><AchievementIcon achievement={item} size={index < 3 ? 29 : 23} /></span>
                <div>
                  <small>{rarityLabel[item.rarity]}</small>
                  <strong>{item.title}</strong>
                  <p>{item.group_title ?? "Глобальний профіль ChatPulse"}</p>
                </div>
              </article>
            ))}
          </div>
          <button className="profile-featured__configure" type="button" onClick={onConfigure}>
            <Settings2 size={17} /> Налаштувати вітрину
          </button>
        </>
      ) : (
        <div className="profile-featured__empty">
          <span><Award size={28} /></span>
          <strong>Твоя вітрина поки порожня</strong>
          <p>Обери до пʼяти найкращих нагород, які бачитимуть у профілі.</p>
          <button type="button" onClick={onConfigure}>
            <Settings2 size={17} /> Налаштувати вітрину
          </button>
        </div>
      )}
    </section>
  );
}
