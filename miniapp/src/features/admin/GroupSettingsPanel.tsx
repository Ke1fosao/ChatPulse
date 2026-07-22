import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Image,
  MessageCircle,
  Palette,
  PauseCircle,
  Radio,
  Reply,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";
import type { GroupSettings, ReportTheme } from "../../api/types";
import { notify } from "../../telegram/sdk";

interface GroupSettingsPanelProps {
  settings: GroupSettings;
  onSave(settings: Partial<GroupSettings>): Promise<GroupSettings>;
  onReset(): Promise<void>;
  onBack(): void;
}

const themes: Array<{ value: ReportTheme; label: string }> = [
  { value: "dark_pulse", label: "Dark Pulse" },
  { value: "telegram_wave", label: "Telegram Wave" },
  { value: "clean_light", label: "Clean Light" },
];

const days = [
  "Понеділок",
  "Вівторок",
  "Середа",
  "Четвер",
  "П’ятниця",
  "Субота",
  "Неділя",
];

export function GroupSettingsPanel({
  settings,
  onSave,
  onReset,
  onBack,
}: GroupSettingsPanelProps) {
  const [draft, setDraft] = useState(settings);
  const [pendingKey, setPendingKey] = useState<keyof GroupSettings | "reset" | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [message, setMessage] = useState("");
  const [messageKind, setMessageKind] = useState<"success" | "error">("success");

  useEffect(() => {
    setDraft(settings);
  }, [settings]);

  const persist = async <K extends keyof GroupSettings>(
    key: K,
    value: GroupSettings[K],
  ) => {
    if (pendingKey !== null) return;

    const previous = draft[key];
    setDraft((current) => ({ ...current, [key]: value }));
    setPendingKey(key);
    setMessage("");

    try {
      const updated = await onSave({ [key]: value } as Partial<GroupSettings>);
      setDraft(updated);
      setMessageKind("success");
      setMessage("Збережено");
      notify("success");
    } catch (error) {
      setDraft((current) => ({ ...current, [key]: previous }));
      setMessageKind("error");
      setMessage(error instanceof Error ? error.message : "Не вдалося зберегти");
      notify("error");
    } finally {
      setPendingKey(null);
    }
  };

  const reset = async () => {
    setPendingKey("reset");
    setMessage("");
    try {
      await onReset();
      notify("success");
      setConfirmReset(false);
      setMessageKind("success");
      setMessage("Статистику групи скинуто");
    } catch (error) {
      setMessageKind("error");
      setMessage(error instanceof Error ? error.message : "Не вдалося скинути статистику");
      notify("error");
    } finally {
      setPendingKey(null);
    }
  };

  const disabled = pendingKey !== null;

  return (
    <div className="group-settings-screen">
      <header className="group-settings-header panel">
        <button
          className="icon-button"
          type="button"
          onClick={onBack}
          aria-label="Назад до групи"
          disabled={disabled}
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <p className="eyebrow">Тільки для адміністраторів</p>
          <h2>Налаштування групи</h2>
          <span>Кожна зміна зберігається автоматично</span>
        </div>
        <ShieldAlert size={22} />
      </header>

      {message ? (
        <div className={`autosave-status autosave-status--${messageKind}`} role="status">
          {messageKind === "success" ? <CheckCircle2 size={16} /> : <ShieldAlert size={16} />}
          {message}
        </div>
      ) : null}

      <section className="settings-section panel">
        <div className="settings-section__heading">
          <span><Clock3 size={18} /></span>
          <div>
            <p className="eyebrow">Розклад</p>
            <h3>Щотижневі звіти</h3>
          </div>
        </div>

        <label className="toggle-row">
          <span><Radio size={17} /> Щотижневі звіти</span>
          <input
            type="checkbox"
            checked={draft.weekly_reports_enabled}
            disabled={disabled}
            onChange={(event) => void persist("weekly_reports_enabled", event.target.checked)}
          />
          <i />
        </label>

        <div className="settings-grid">
          <label className="setting-control">
            <span><Clock3 size={17} /> Час звіту</span>
            <input
              aria-label="Час звіту"
              type="time"
              value={draft.report_time}
              disabled={disabled}
              onChange={(event) => void persist("report_time", event.target.value)}
            />
          </label>

          <label className="setting-control">
            <span>День звіту</span>
            <select
              aria-label="День звіту"
              value={draft.report_weekday}
              disabled={disabled}
              onChange={(event) => void persist("report_weekday", Number(event.target.value))}
            >
              {days.map((day, index) => (
                <option key={day} value={index}>{day}</option>
              ))}
            </select>
          </label>

          <label className="setting-control setting-control--wide">
            <span>Часовий пояс</span>
            <select
              aria-label="Часовий пояс"
              value={draft.timezone}
              disabled={disabled}
              onChange={(event) =>
                void persist("timezone", event.target.value as GroupSettings["timezone"])
              }
            >
              <option value="Europe/Kyiv">Україна · Київ</option>
              <option value="Europe/Warsaw">Польща · Варшава</option>
              <option value="Europe/Berlin">Німеччина · Берлін</option>
            </select>
          </label>
        </div>
      </section>

      <section className="settings-section panel">
        <div className="settings-section__heading">
          <span><MessageCircle size={18} /></span>
          <div>
            <p className="eyebrow">Аналітика</p>
            <h3>Збір даних</h3>
          </div>
        </div>
        <p className="settings-section__description">
          ChatPulse не зберігає тексти повідомлень або файли — лише агреговані лічильники.
        </p>
        <div className="toggle-list">
          {([
            ["track_messages", "Повідомлення", <MessageCircle size={17} />],
            ["track_media", "Медіа", <Image size={17} />],
            ["track_replies", "Відповіді", <Reply size={17} />],
            ["track_reactions", "Реакції", <Radio size={17} />],
          ] as const).map(([key, label, icon]) => (
            <label className="toggle-row" key={key}>
              <span>{icon} {label}</span>
              <input
                type="checkbox"
                checked={draft[key]}
                disabled={disabled}
                onChange={(event) => void persist(key, event.target.checked)}
              />
              <i />
            </label>
          ))}
        </div>
      </section>

      <section className="settings-section panel">
        <div className="settings-section__heading">
          <span><Palette size={18} /></span>
          <div>
            <p className="eyebrow">Вигляд</p>
            <h3>Оформлення картки</h3>
          </div>
        </div>
        <label className="setting-control setting-control--wide">
          <span><Palette size={17} /> Тема звіту</span>
          <select
            aria-label="Тема звіту"
            value={draft.report_card_theme}
            disabled={disabled}
            onChange={(event) =>
              void persist("report_card_theme", event.target.value as ReportTheme)
            }
          >
            {themes.map((theme) => (
              <option key={theme.value} value={theme.value}>{theme.label}</option>
            ))}
          </select>
        </label>
      </section>

      <section className="settings-section panel">
        <div className="settings-section__heading">
          <span><PauseCircle size={18} /></span>
          <div>
            <p className="eyebrow">Робота бота</p>
            <h3>Стан статистики</h3>
          </div>
        </div>
        <label className="toggle-row toggle-row--warning">
          <span><PauseCircle size={17} /> Призупинити статистику</span>
          <input
            type="checkbox"
            checked={draft.is_paused}
            disabled={disabled}
            onChange={(event) => void persist("is_paused", event.target.checked)}
          />
          <i />
        </label>
        <p className="settings-section__description">
          Пауза не видаляє попередні дані. Збір можна відновити у будь-який момент.
        </p>
      </section>

      <section className="settings-section settings-section--danger panel">
        <div className="settings-section__heading">
          <span><Trash2 size={18} /></span>
          <div>
            <p className="eyebrow">Обережно</p>
            <h3>Небезпечна зона</h3>
          </div>
        </div>
        {!confirmReset ? (
          <button
            className="danger-button"
            type="button"
            onClick={() => setConfirmReset(true)}
            disabled={disabled}
          >
            <Trash2 size={17} /> Скинути статистику
          </button>
        ) : (
          <div className="danger-confirm">
            <p>Це видалить статистику, XP, серії та досягнення цієї групи.</p>
            <div>
              <button type="button" onClick={() => setConfirmReset(false)} disabled={disabled}>
                Скасувати
              </button>
              <button type="button" onClick={() => void reset()} disabled={disabled}>
                {pendingKey === "reset" ? "Скидаємо…" : "Так, скинути"}
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
