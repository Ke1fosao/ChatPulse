import { Download, Share2, X } from "lucide-react";
import { useState } from "react";
import { api, downloadBlob } from "../api/client";
import type { HomePayload } from "../api/types";
import { notify } from "../telegram/sdk";

interface ShareCardDialogProps {
  data: HomePayload;
  open: boolean;
  onClose(): void;
}

export function ShareCardDialog({ data, open, onClose }: ShareCardDialogProps) {
  const [downloading, setDownloading] = useState(false);
  if (!open) return null;

  const share = async () => {
    const text = `Мій ChatPulse: рівень ${data.global_progress.level}, ${data.global_progress.xp_total} XP і серія ${data.quick_stats.current_streak} днів.`;
    try {
      if (navigator.share) {
        await navigator.share({ title: "Мій ChatPulse", text });
      } else {
        await navigator.clipboard.writeText(text);
      }
      notify("success");
    } catch {
      notify("warning");
    }
  };

  const download = async () => {
    setDownloading(true);
    try {
      downloadBlob(await api.profileCard(), "chatpulse-profile.png");
      notify("success");
    } catch {
      notify("error");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="dialog-backdrop" role="presentation" onClick={onClose}>
      <section
        className="share-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Поділитися профілем"
        onClick={(event) => event.stopPropagation()}
      >
        <button className="dialog-close" type="button" onClick={onClose} aria-label="Закрити">
          <X size={20} />
        </button>
        <div className="share-preview">
          <span className="share-preview__brand">ChatPulse</span>
          <div className="share-preview__level">
            <small>LEVEL</small>
            <strong>{data.global_progress.level}</strong>
          </div>
          <h2>{data.user.display_name}</h2>
          <p>{data.global_progress.tier} · {data.global_progress.xp_total.toLocaleString("uk-UA")} XP</p>
          <div>
            <span>🔥 {data.quick_stats.current_streak} днів</span>
            <span>🏆 #{data.global_progress.rank}</span>
          </div>
        </div>
        <div className="share-actions">
          <button className="primary-button" type="button" onClick={share}>
            <Share2 size={18} /> Поділитися
          </button>
          <button className="secondary-button" type="button" onClick={download} disabled={downloading}>
            <Download size={18} /> {downloading ? "Генеруємо…" : "PNG-картка"}
          </button>
        </div>
      </section>
    </div>
  );
}
