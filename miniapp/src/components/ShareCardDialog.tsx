import { Check, Copy, Download, LoaderCircle, Send, Share2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { api, downloadBlob } from "../api/client";
import type { HomePayload } from "../api/types";
import { notify, openTelegramLink } from "../telegram/sdk";

interface ShareCardDialogProps {
  data: HomePayload;
  open: boolean;
  onClose(): void;
}

function roleLabel(data: HomePayload): string {
  if (data.account.is_owner) return "OWNER · CREATOR";
  if (data.account.is_vip) return "VIP CLIENT";
  return "MEMBER · FREE";
}

export function ShareCardDialog({ data, open, onClose }: ShareCardDialogProps) {
  const [card, setCard] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "shared" | "copied" | "downloaded">("idle");
  const shareText = useMemo(
    () => `Мій ChatPulse — ${roleLabel(data)}, рівень ${data.global_progress.level} (${data.global_progress.tier}), ${data.global_progress.xp_total} XP, місце #${data.global_progress.rank} і серія ${data.quick_stats.current_streak} днів.`,
    [data],
  );

  useEffect(() => {
    if (!open || card) return;
    setLoading(true);
    void api.profileCard()
      .then((blob) => {
        setCard(blob);
        setPreviewUrl(URL.createObjectURL(blob));
      })
      .catch(() => notify("error"))
      .finally(() => setLoading(false));
  }, [card, open]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  useEffect(() => {
    if (!open) return;
    document.body.classList.add("share-dialog-open");
    return () => document.body.classList.remove("share-dialog-open");
  }, [open]);

  if (!open) return null;

  const shareFile = async () => {
    try {
      const file = card ? new File([card], "chatpulse-profile.png", { type: "image/png" }) : null;
      if (file && navigator.share && (!navigator.canShare || navigator.canShare({ files: [file] }))) {
        await navigator.share({
          title: "Мій ChatPulse",
          text: shareText,
          files: [file],
        });
      } else if (navigator.share) {
        await navigator.share({ title: "Мій ChatPulse", text: shareText });
      } else {
        openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(window.location.origin)}&text=${encodeURIComponent(shareText)}`);
      }
      setStatus("shared");
      notify("success");
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      notify("warning");
    }
  };

  const download = async () => {
    try {
      const blob = card ?? await api.profileCard();
      downloadBlob(blob, `chatpulse-${data.user.username ?? data.user.telegram_id}.png`);
      setStatus("downloaded");
      notify("success");
    } catch {
      notify("error");
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareText);
      setStatus("copied");
      notify("success");
    } catch {
      notify("error");
    }
  };

  return createPortal(
    <div className="dialog-backdrop share-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="share-dialog share-dialog--premium"
        role="dialog"
        aria-modal="true"
        aria-label="Поділитися профілем"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="share-dialog__header">
          <div>
            <p className="eyebrow">Твоя картка</p>
            <h2>Поділись прогресом</h2>
            <span>Готова PNG-картка з роллю, рівнем і статистикою</span>
          </div>
          <button className="dialog-close" type="button" onClick={onClose} aria-label="Закрити">
            <X size={20} />
          </button>
        </header>

        <div className="share-image-frame">
          {loading ? (
            <div className="share-image-loading"><LoaderCircle className="spin" /> Генеруємо картку…</div>
          ) : previewUrl ? (
            <img src={previewUrl} alt="Попередній перегляд PNG-картки ChatPulse" />
          ) : (
            <div className="share-preview share-preview--fallback">
              <span className="share-preview__brand">ChatPulse</span>
              <strong>{roleLabel(data)}</strong>
              <h2>{data.user.display_name}</h2>
              <p>LEVEL {data.global_progress.level} · {data.global_progress.xp_total.toLocaleString("uk-UA")} XP</p>
            </div>
          )}
        </div>

        <div className="share-primary-actions">
          <button className="primary-button" type="button" onClick={() => void shareFile()} disabled={loading}>
            {status === "shared" ? <Check size={19} /> : <Share2 size={19} />}
            {status === "shared" ? "Надіслано" : "Поділитися карткою"}
          </button>
          <button className="secondary-button" type="button" onClick={() => void download()} disabled={loading}>
            {status === "downloaded" ? <Check size={19} /> : <Download size={19} />}
            {status === "downloaded" ? "Збережено" : "Зберегти PNG"}
          </button>
        </div>

        <div className="share-secondary-actions">
          <button type="button" onClick={() => openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(window.location.origin)}&text=${encodeURIComponent(shareText)}`)}>
            <Send size={17} /> Telegram
          </button>
          <button type="button" onClick={() => void copy()}>
            {status === "copied" ? <Check size={17} /> : <Copy size={17} />}
            {status === "copied" ? "Скопійовано" : "Скопіювати текст"}
          </button>
        </div>
      </section>
    </div>,
    document.body,
  );
}
