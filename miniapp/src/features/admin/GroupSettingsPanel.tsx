import { Clock3, PauseCircle, Save, ShieldAlert, Trash2 } from "lucide-react";
import { useState } from "react";
import type { GroupSettings, ReportTheme } from "../../api/types";
import { notify } from "../../telegram/sdk";

interface GroupSettingsPanelProps {
  settings: GroupSettings;
  onSave(settings: Partial<GroupSettings>): Promise<GroupSettings>;
  onReset(): Promise<void>;
}

const themes: Array<{ value: ReportTheme; label: string }> = [
  { value: "dark_pulse", label: "Dark Pulse" },
  { value: "telegram_wave", label: "Telegram Wave" },
  { value: "clean_light", label: "Clean Light" },
];

export function GroupSettingsPanel({
  settings,
  onSave,
  onReset,
}: GroupSettingsPanelProps) {
  const [draft, setDraft] = useState(settings);
  const [saving, setSaving] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [message, setMessage] = useState("");

  const update = <K extends keyof GroupSettings>(key: K, value: GroupSettings[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const save = async () => {
    setSaving(true);
    setMessage("");
    try {
      const updated = await onSave(draft);
      setDraft(updated);
      setMessage("Налаштування збережено");
      notify("success");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не вдалося зберегти");
      notify("error");
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    setSaving(true);
    try {
      await onReset();
      notify("success");
      setConfirmReset(false);
      setMessage("Статистику групи скинуто");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не вдалося скинути статистику");
      notify("error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="settings-panel panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Тільки для адміністраторів</p>
          <h2>Керування групою</h2>
        </div>
        <ShieldAlert size={22} />
      </div>

      <div className="settings-grid">
        <label className="setting-control">
          <span>
            <Clock3 size={17} /> Час звіту
          </span>
          <input
            type="time"
            value={draft.report_time}
            onChange={(event) => update("report_time", event.target.value)}
          />
        </label>

        <label className="setting-control">
          <span>День звіту</span>
          <select
            value={draft.report_weekday}
            onChange={(event) => update("report_weekday", Number(event.target.value))}
          >
            {['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П’ятниця', 'Субота', 'Неділя'].map(
              (day, index) => (
                <option key={day} value={index}>{day}</option>
              ),
            )}
          </select>
        </label>

        <label className="setting-control">
          <span>Часовий пояс</span>
          <select
            value={draft.timezone}
            onChange={(event) => update("timezone", event.target.value as GroupSettings["timezone"])}
          >
            <option value="Europe/Kyiv">Україна · Київ</option>
            <option value="Europe/Warsaw">Польща · Варшава</option>
            <option value="Europe/Berlin">Німеччина · Берлін</option>
          </select>
        </label>

        <label className="setting-control">
          <span>Тема картки</span>
          <select
            value={draft.report_card_theme}
            onChange={(event) => update("report_card_theme", event.target.value as ReportTheme)}
          >
            {themes.map((theme) => (
              <option key={theme.value} value={theme.value}>{theme.label}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="toggle-list">
        {([
          ["weekly_reports_enabled", "Щотижневі звіти"],
          ["track_messages", "Повідомлення"],
          ["track_media", "Медіа"],
          ["track_replies", "Відповіді"],
          ["track_reactions", "Реакції"],
        ] as const).map(([key, label]) => (
          <label className="toggle-row" key={key}>
            <span>{label}</span>
            <input
              type="checkbox"
              checked={draft[key]}
              onChange={(event) => update(key, event.target.checked)}
            />
            <i />
          </label>
        ))}
        <label className="toggle-row toggle-row--warning">
          <span><PauseCircle size={17} /> Призупинити статистику</span>
          <input
            type="checkbox"
            checked={draft.is_paused}
            onChange={(event) => update("is_paused", event.target.checked)}
          />
          <i />
        </label>
      </div>

      {message ? <p className="form-message">{message}</p> : null}
      <button className="primary-button" type="button" onClick={save} disabled={saving}>
        <Save size={18} /> {saving ? "Збереження…" : "Зберегти зміни"}
      </button>

      <div className="danger-zone">
        {!confirmReset ? (
          <button className="danger-button" type="button" onClick={() => setConfirmReset(true)}>
            <Trash2 size={17} /> Скинути статистику
          </button>
        ) : (
          <div className="danger-confirm">
            <p>Це видалить статистику, XP і досягнення цієї групи.</p>
            <div>
              <button type="button" onClick={() => setConfirmReset(false)}>Скасувати</button>
              <button type="button" onClick={reset} disabled={saving}>Так, скинути</button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
