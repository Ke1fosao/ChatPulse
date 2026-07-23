import { Check, Crown, GripVertical, LockKeyhole, RefreshCw, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { AccountAccess, Achievement } from "../../api/types";
import { VipUpgradeCard } from "../../premium/VipUpgradeCard";
import { notify } from "../../telegram/sdk";
import { vipApi } from "../../vip/vipApi";

interface FeaturedAchievementsProps {
  account: AccountAccess;
  achievements: Achievement[];
  trialAvailable: boolean;
  onOpenVip(source: string, featureKey?: string | null): void;
}

export function FeaturedAchievements({
  account,
  achievements,
  trialAvailable,
  onOpenVip,
}: FeaturedAchievementsProps) {
  const unlocked = account.is_owner || account.is_vip;
  const earned = useMemo(
    () => achievements.filter((item) => item.earned && !item.hidden),
    [achievements],
  );
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!unlocked) return;
    void vipApi
      .featured()
      .then((items) => setSelected(items.map((item) => item.code)))
      .catch(() => setMessage("Не вдалося завантажити закріплені нагороди."));
  }, [unlocked]);

  const toggle = (code: string) => {
    setMessage("");
    setSelected((current) => {
      if (current.includes(code)) return current.filter((item) => item !== code);
      if (current.length >= 5) {
        setMessage("Можна закріпити максимум пʼять досягнень.");
        return current;
      }
      return [...current, code];
    });
  };

  const save = async () => {
    setBusy(true);
    setMessage("");
    try {
      const items = await vipApi.updateFeatured(selected);
      setSelected(items.map((item) => item.code));
      setMessage("Закріплені досягнення оновлено.");
      notify("success");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Не вдалося зберегти.");
      notify("error");
    } finally {
      setBusy(false);
    }
  };

  if (!unlocked) {
    return (
      <section className="featured-achievements-block">
        <div className="section-heading">
          <div><p className="eyebrow">Профіль</p><h2>Закріплені досягнення</h2></div>
          <Crown size={21} />
        </div>
        <div className="featured-slot-row" aria-label="VIP-слоти досягнень">
          {Array.from({ length: 5 }, (_, index) => (
            <span aria-label="Порожній VIP-слот" key={index}><LockKeyhole size={17} /></span>
          ))}
        </div>
        <VipUpgradeCard
          title="Покажи найкращі нагороди"
          description="Закріпи до пʼяти отриманих досягнень у профілі."
          source="featured_achievements"
          featureKey="profile.featured_achievements"
          trialAvailable={trialAvailable}
          onOpen={onOpenVip}
        />
      </section>
    );
  }

  return (
    <section className="featured-achievements-block panel">
      <div className="section-heading">
        <div><p className="eyebrow">Профіль</p><h2>Закріплені досягнення</h2></div>
        <span className="count-pill">{selected.length}/5</span>
      </div>
      <div className="featured-slot-row is-active">
        {Array.from({ length: 5 }, (_, index) => {
          const code = selected[index];
          const achievement = earned.find((item) => item.code === code);
          return achievement ? (
            <span key={code} title={achievement.title}>
              <GripVertical size={13} />
              <b>{achievement.icon}</b>
            </span>
          ) : (
            <span aria-label="Порожній VIP-слот" key={`empty-${index}`} />
          );
        })}
      </div>
      <div className="featured-achievement-options">
        {earned.slice(0, 24).map((achievement) => {
          const active = selected.includes(achievement.code);
          return (
            <button
              type="button"
              className={active ? "is-selected" : ""}
              key={achievement.code}
              onClick={() => toggle(achievement.code)}
            >
              <span>{achievement.icon}</span>
              <div><strong>{achievement.title}</strong><small>{achievement.description}</small></div>
              {active ? <Check size={17} /> : null}
            </button>
          );
        })}
      </div>
      {message ? <p className="featured-achievement-message">{message}</p> : null}
      <button className="primary-button" type="button" disabled={busy} onClick={() => void save()}>
        {busy ? <RefreshCw className="spin" size={17} /> : <Save size={17} />}
        Зберегти у профілі
      </button>
    </section>
  );
}
