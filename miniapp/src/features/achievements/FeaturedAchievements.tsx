import {
  ArrowDown,
  ArrowUp,
  Check,
  Crown,
  GripVertical,
  LockKeyhole,
  RefreshCw,
  Save,
  Search,
  Settings2,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import type {
  AccountAccess,
  Achievement,
  AchievementEarnedInstance,
  AchievementRarity,
} from "../../api/types";
import { VipUpgradeCard } from "../../premium/VipUpgradeCard";
import { notify } from "../../telegram/sdk";
import type {
  FeaturedAchievement,
  FeaturedAchievementSelection,
} from "../../vip/types";
import { vipApi } from "../../vip/vipApi";
import { AchievementIcon, rarityLabel } from "./AchievementVisual";

interface FeaturedAchievementsProps {
  account: AccountAccess;
  achievements: Achievement[];
  trialAvailable: boolean;
  onOpenVip(source: string, featureKey?: string | null): void;
}

interface ShowcaseChoice {
  id: string;
  code: string;
  scopeKey: string;
  achievement: Achievement;
  instance: AchievementEarnedInstance;
}

const rarityOptions: Array<["all" | AchievementRarity, string]> = [
  ["all", "Усі рідкості"],
  ["common", "Звичайні"],
  ["uncommon", "Незвичайні"],
  ["rare", "Рідкісні"],
  ["epic", "Епічні"],
  ["legendary", "Легендарні"],
  ["secret", "Секретні"],
];

function identity(code: string, scopeKey: string): string {
  return `${code}::${scopeKey}`;
}

function fallbackInstance(achievement: Achievement): AchievementEarnedInstance | null {
  const scopeKey =
    achievement.primary_scope_key ??
    (achievement.scope === "global" ? "global" : null);
  if (!achievement.earned || !scopeKey || !achievement.earned_at) return null;
  return {
    scope_key: scopeKey,
    telegram_chat_id:
      scopeKey.startsWith("group:")
        ? Number(scopeKey.replace("group:", ""))
        : null,
    group_title: achievement.group_title ?? null,
    earned_at: achievement.earned_at,
    progress: achievement.progress,
  };
}

function choicesFromAchievements(achievements: Achievement[]): ShowcaseChoice[] {
  return achievements.flatMap((achievement) => {
    if (!achievement.earned) return [];
    const instances = achievement.earned_instances?.length
      ? achievement.earned_instances
      : [fallbackInstance(achievement)].filter(
          (item): item is AchievementEarnedInstance => item !== null,
        );
    return instances.map((instance) => ({
      id: identity(achievement.code, instance.scope_key),
      code: achievement.code,
      scopeKey: instance.scope_key,
      achievement,
      instance,
    }));
  });
}

function choiceFromFeatured(item: FeaturedAchievement): ShowcaseChoice {
  const instance = item.earned_instances?.[0] ?? {
    scope_key: item.scope_key,
    telegram_chat_id: item.scope_key.startsWith("group:")
      ? Number(item.scope_key.replace("group:", ""))
      : null,
    group_title: item.group_title ?? null,
    earned_at: item.earned_at ?? new Date().toISOString(),
    progress: item.progress,
  };
  return {
    id: identity(item.code, item.scope_key),
    code: item.code,
    scopeKey: item.scope_key,
    achievement: item,
    instance,
  };
}

function groupLabel(choice: ShowcaseChoice): string {
  return choice.instance.group_title ??
    (choice.scopeKey === "global" ? "Глобальний профіль" : "Групове досягнення");
}

function ShowcaseSlot({ choice, index }: { choice?: ShowcaseChoice; index: number }) {
  return choice ? (
    <article
      className={`featured-showcase-slot featured-showcase-slot--${choice.achievement.rarity}`}
      title={`${choice.achievement.title} · ${groupLabel(choice)}`}
    >
      <span><AchievementIcon achievement={choice.achievement} size={24} /></span>
      <small>#{index + 1}</small>
      <strong>{choice.achievement.title}</strong>
    </article>
  ) : (
    <article className="featured-showcase-slot is-empty" aria-label="Порожній VIP-слот">
      <span><LockKeyhole size={20} /></span>
      <small>#{index + 1}</small>
      <strong>Порожньо</strong>
    </article>
  );
}

export function FeaturedAchievements({
  account,
  achievements,
  trialAvailable,
  onOpenVip,
}: FeaturedAchievementsProps) {
  const unlocked = account.is_owner || account.is_vip;
  const available = useMemo(
    () => choicesFromAchievements(achievements),
    [achievements],
  );
  const [selected, setSelected] = useState<ShowcaseChoice[]>([]);
  const [editorOpen, setEditorOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [rarity, setRarity] = useState<"all" | AchievementRarity>("all");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [draggingId, setDraggingId] = useState<string | null>(null);

  useEffect(() => {
    if (!unlocked) return;
    setLoading(true);
    void vipApi
      .featured()
      .then((items) => {
        setSelected(
          items.map((item) =>
            available.find(
              (choice) =>
                choice.code === item.code && choice.scopeKey === item.scope_key,
            ) ?? choiceFromFeatured(item),
          ),
        );
      })
      .catch(() => setMessage("Не вдалося завантажити вітрину нагород."))
      .finally(() => setLoading(false));
  }, [available, unlocked]);

  useEffect(() => {
    if (!editorOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setEditorOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [editorOpen]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("uk-UA");
    return available.filter((choice) => {
      if (rarity !== "all" && choice.achievement.rarity !== rarity) return false;
      if (!normalized) return true;
      return [
        choice.achievement.title,
        choice.achievement.description,
        groupLabel(choice),
      ].some((value) => value.toLocaleLowerCase("uk-UA").includes(normalized));
    });
  }, [available, query, rarity]);

  const toggle = (choice: ShowcaseChoice) => {
    setMessage("");
    setSelected((current) => {
      if (current.some((item) => item.id === choice.id)) {
        return current.filter((item) => item.id !== choice.id);
      }
      if (current.length >= 5) {
        setMessage("Можна закріпити максимум пʼять досягнень.");
        return current;
      }
      return [...current, choice];
    });
  };

  const move = (index: number, direction: -1 | 1) => {
    setSelected((current) => {
      const target = index + direction;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  const moveByDrop = (targetId: string) => {
    if (!draggingId || draggingId === targetId) return;
    setSelected((current) => {
      const sourceIndex = current.findIndex((item) => item.id === draggingId);
      const targetIndex = current.findIndex((item) => item.id === targetId);
      if (sourceIndex < 0 || targetIndex < 0) return current;
      const next = [...current];
      const [moved] = next.splice(sourceIndex, 1);
      next.splice(targetIndex, 0, moved);
      return next;
    });
    setDraggingId(null);
  };

  const save = async () => {
    setBusy(true);
    setMessage("");
    try {
      const payload: FeaturedAchievementSelection[] = selected.map((item) => ({
        code: item.code,
        scope_key: item.scopeKey,
      }));
      const items = await vipApi.updateFeatured(payload);
      setSelected(items.map(choiceFromFeatured));
      setMessage("Вітрину нагород оновлено.");
      setEditorOpen(false);
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
          <div><p className="eyebrow">Профіль</p><h2>Вітрина нагород</h2></div>
          <Crown size={22} />
        </div>
        <div className="featured-showcase-grid" aria-label="VIP-слоти досягнень">
          {Array.from({ length: 5 }, (_, index) => (
            <ShowcaseSlot index={index} key={index} />
          ))}
        </div>
        <VipUpgradeCard
          title="Покажи найкращі нагороди"
          description="Закріпи до пʼяти конкретних досягнень у своєму профілі."
          source="featured_achievements"
          featureKey="profile.featured_achievements"
          trialAvailable={trialAvailable}
          onOpen={onOpenVip}
        />
      </section>
    );
  }

  const editor = editorOpen
    ? createPortal(
        <div className="featured-editor" role="dialog" aria-modal="true" aria-label="Редактор вітрини нагород">
          <button
            className="featured-editor__backdrop"
            type="button"
            aria-label="Закрити редактор"
            onClick={() => setEditorOpen(false)}
          />
          <section className="featured-editor__sheet">
            <header>
              <div>
                <p className="eyebrow">Твій профіль</p>
                <h2>Налаштуй вітрину</h2>
                <span>{selected.length}/5 нагород вибрано</span>
              </div>
              <button className="dialog-close" type="button" aria-label="Закрити" onClick={() => setEditorOpen(false)}>
                <X size={20} />
              </button>
            </header>

            <div className="featured-editor__selected">
              <strong>Порядок у профілі</strong>
              {selected.length ? (
                <div className="featured-editor__order-list">
                  {selected.map((choice, index) => (
                    <article
                      draggable
                      key={choice.id}
                      onDragStart={() => setDraggingId(choice.id)}
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={() => moveByDrop(choice.id)}
                    >
                      <GripVertical size={18} />
                      <span><AchievementIcon achievement={choice.achievement} size={22} /></span>
                      <div>
                        <strong>{choice.achievement.title}</strong>
                        <small>{groupLabel(choice)}</small>
                      </div>
                      <div className="featured-editor__order-actions">
                        <button
                          type="button"
                          disabled={index === 0}
                          aria-label={`Перемістити ${choice.achievement.title} вище`}
                          onClick={() => move(index, -1)}
                        >
                          <ArrowUp size={17} />
                        </button>
                        <button
                          type="button"
                          disabled={index === selected.length - 1}
                          aria-label={`Перемістити ${choice.achievement.title} нижче`}
                          onClick={() => move(index, 1)}
                        >
                          <ArrowDown size={17} />
                        </button>
                        <button
                          type="button"
                          aria-label={`Прибрати ${choice.achievement.title}`}
                          onClick={() => toggle(choice)}
                        >
                          <Trash2 size={17} />
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <p>Обери нагороди нижче — перші три будуть найбільш помітними.</p>
              )}
            </div>

            <div className="featured-editor__filters">
              <label>
                <Search size={18} />
                <input
                  type="search"
                  aria-label="Пошук нагород"
                  placeholder="Назва, опис або група"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
              <select
                aria-label="Рідкість нагород"
                value={rarity}
                onChange={(event) =>
                  setRarity(event.target.value as "all" | AchievementRarity)
                }
              >
                {rarityOptions.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>

            <div className="featured-editor__catalog">
              {filtered.length ? filtered.map((choice) => {
                const active = selected.some((item) => item.id === choice.id);
                return (
                  <button
                    type="button"
                    className={active ? "is-selected" : ""}
                    key={choice.id}
                    aria-label={`${choice.achievement.title} · ${groupLabel(choice)}`}
                    onClick={() => toggle(choice)}
                  >
                    <span className={`featured-editor__catalog-icon is-${choice.achievement.rarity}`}>
                      <AchievementIcon achievement={choice.achievement} size={24} />
                    </span>
                    <div>
                      <strong>{choice.achievement.title}</strong>
                      <small>{groupLabel(choice)} · {rarityLabel[choice.achievement.rarity]}</small>
                      <p>{choice.achievement.description}</p>
                    </div>
                    {active ? <Check size={19} /> : null}
                  </button>
                );
              }) : (
                <p className="featured-editor__empty">За цим пошуком нагород немає.</p>
              )}
            </div>

            {message ? <p className="featured-achievement-message">{message}</p> : null}
            <button className="primary-button featured-editor__save" type="button" disabled={busy} onClick={() => void save()}>
              {busy ? <RefreshCw className="spin" size={18} /> : <Save size={18} />}
              Зберегти вітрину
            </button>
          </section>
        </div>,
        document.body,
      )
    : null;

  return (
    <>
      <section className="featured-achievements-block panel">
        <div className="section-heading">
          <div><p className="eyebrow">Профіль</p><h2>Вітрина нагород</h2></div>
          <span className="count-pill">{selected.length}/5</span>
        </div>
        <div className="featured-showcase-grid is-active">
          {Array.from({ length: 5 }, (_, index) => (
            <ShowcaseSlot choice={selected[index]} index={index} key={selected[index]?.id ?? `empty-${index}`} />
          ))}
        </div>
        <p className="featured-showcase-help">
          Перші три нагороди відображаються великими у профілі та на картці для поширення.
        </p>
        {message ? <p className="featured-achievement-message">{message}</p> : null}
        <button
          className="secondary-button featured-showcase-configure"
          type="button"
          disabled={loading}
          onClick={() => setEditorOpen(true)}
        >
          {loading ? <RefreshCw className="spin" size={18} /> : <Settings2 size={18} />}
          Налаштувати вітрину
        </button>
      </section>
      {editor}
    </>
  );
}
