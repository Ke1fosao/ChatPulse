import {
  Check,
  Copy,
  Download,
  Image as ImageIcon,
  LoaderCircle,
  Send,
  Share2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { api, downloadBlob } from "../api/client";
import type { HomePayload } from "../api/types";
import {
  buildProfileShareText,
  getProfileStatus,
  profileCardFilename,
} from "../features/profile/profileStatus";
import { notify, openTelegramLink } from "../telegram/sdk";

interface ShareCardDialogProps {
  data: HomePayload;
  open: boolean;
  onClose(): void;
}

type ActionState = "idle" | "sharing" | "saving" | "copying" | "shared" | "saved" | "copied";

export function ShareCardDialog({ data, open, onClose }: ShareCardDialogProps) {
  const [cardBlob, setCardBlob] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [action, setAction] = useState<ActionState>("idle");
  const status = useMemo(() => getProfileStatus(data.account), [data.account]);
  const filename = useMemo(() => profileCardFilename(data), [data]);
  const shareText = useMemo(() => buildProfileShareText(data), [data]);

  useEffect(() => {
    if (!open) return undefined;

    let active = true;
    let currentUrl = "";
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.body.classList.add("profile-dialog-open");
    setLoading(true);
    setError("");
    setAction("idle");

    void api.profileCard()
      .then((blob) => {
        if (!active) return;
        currentUrl = URL.createObjectURL(blob);
        setCardBlob(blob);
        setPreviewUrl(currentUrl);
      })
      .catch(() => {
        if (!active) return;
        setError("Не вдалося згенерувати PNG-картку. Спробуй ще раз.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);

    return () => {
      active = false;
      document.body.style.overflow = previousOverflow;
      document.body.classList.remove("profile-dialog-open");
      window.removeEventListener("keydown", onKeyDown);
      if (currentUrl) URL.revokeObjectURL(currentUrl);
      setCardBlob(null);
      setPreviewUrl("");
    };
  }, [onClose, open]);

  if (!open) return null;

  const ensureCard = async (): Promise<Blob> => {
    if (cardBlob) return cardBlob;
    const blob = await api.profileCard();
    setCardBlob(blob);
    if (!previewUrl) setPreviewUrl(URL.createObjectURL(blob));
    return blob;
  };

  const resetActionLater = () => {
    window.setTimeout(() => setAction("idle"), 1400);
  };

  const share = async () => {
    setAction("sharing");
    try {
      const blob = await ensureCard();
      const file = new File([blob], filename, { type: "image/png" });
      const filePayload: ShareData = {
        title: `ChatPulse · ${data.user.display_name}`,
        text: shareText,
        files: [file],
      };

      if (navigator.share && navigator.canShare?.({ files: [file] })) {
        await navigator.share(filePayload);
      } else if (navigator.share) {
        await navigator.share({
          title: `ChatPulse · ${data.user.display_name}`,
          text: shareText,
          url: `${window.location.origin}/miniapp`,
        });
      } else {
        const url = encodeURIComponent(`${window.location.origin}/miniapp`);
        const text = encodeURIComponent(shareText);
        openTelegramLink(`https://t.me/share/url?url=${url}&text=${text}`);
      }
      setAction("shared");
      notify("success");
      resetActionLater();
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") {
        setAction("idle");
        return;
      }
      setAction("idle");
      notify("warning");
    }
  };

  const save = async () => {
    setAction("saving");
    try {
      downloadBlob(await ensureCard(), filename);
      setAction("saved");
      notify("success");
      resetActionLater();
    } catch {
      setAction("idle");
      notify("error");
    }
  };

  const shareToTelegram = () => {
    const url = encodeURIComponent(`${window.location.origin}/miniapp`);
    const text = encodeURIComponent(shareText);
    openTelegramLink(`https://t.me/share/url?url=${url}&text=${text}`);
    notify("success");
  };

  const copy = async () => {
    setAction("copying");
    try {
      const value = `${shareText}\n${window.location.origin}/miniapp`;
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        const input = document.createElement("textarea");
        input.value = value;
        input.style.position = "fixed";
        input.style.opacity = "0";
        document.body.appendChild(input);
        input.select();
        document.execCommand("copy");
        input.remove();
      }
      setAction("copied");
      notify("success");
      resetActionLater();
    } catch {
      setAction("idle");
      notify("error");
    }
  };

  return createPortal(
    <div
      className="dialog-backdrop share-dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="share-dialog share-dialog--v2"
        role="dialog"
        aria-modal="true"
        aria-label="Поділитися профілем"
      >
        <header className="share-dialog__header">
          <div>
            <p className="eyebrow">Готово для Telegram</p>
            <h2>Твоя профільна картка</h2>
            <span>PNG 1200 × 1200 · без текстів повідомлень</span>
          </div>
          <button className="dialog-close" type="button" onClick={onClose} aria-label="Закрити">
            <X size={20} />
          </button>
        </header>

        <div className={`share-card-frame share-card-frame--${status.tone}`}>
          <div className="share-card-frame__badges">
            <span>{status.role}</span>
            <span>{status.plan}</span>
          </div>
          {loading ? (
            <div className="share-card-loading">
              <LoaderCircle className="spin" size={30} />
              <strong>Генеруємо PNG…</strong>
              <small>Створюємо актуальну картку з твоїм рівнем і статусом</small>
            </div>
          ) : previewUrl ? (
            <img src={previewUrl} alt="PNG-картка профілю ChatPulse" />
          ) : (
            <div className="share-card-loading share-card-loading--error">
              <ImageIcon size={30} />
              <strong>Картка недоступна</strong>
              <small>{error}</small>
            </div>
          )}
        </div>

        <div className="share-dialog__summary">
          <div>
            <small>Рівень</small>
            <strong>{data.global_progress.level}/{data.level_catalog.max_level}</strong>
          </div>
          <div>
            <small>Статус</small>
            <strong>{status.role}</strong>
          </div>
          <div>
            <small>Місце</small>
            <strong>#{data.global_progress.rank}</strong>
          </div>
        </div>

        {error ? <p className="share-dialog__error">{error}</p> : null}

        <div className="share-actions share-actions--v2">
          <button
            className="primary-button share-primary-action"
            type="button"
            onClick={() => void share()}
            disabled={loading || action === "sharing"}
          >
            {action === "sharing" ? (
              <LoaderCircle className="spin" size={18} />
            ) : action === "shared" ? (
              <Check size={18} />
            ) : (
              <Share2 size={18} />
            )}
            {action === "sharing"
              ? "Готуємо файл…"
              : action === "shared"
                ? "Відкрито"
                : "Поділитися карткою"}
          </button>

          <button
            className="secondary-button"
            type="button"
            onClick={() => void save()}
            disabled={loading || action === "saving"}
          >
            {action === "saving" ? (
              <LoaderCircle className="spin" size={18} />
            ) : action === "saved" ? (
              <Check size={18} />
            ) : (
              <Download size={18} />
            )}
            {action === "saving" ? "Зберігаємо…" : action === "saved" ? "Збережено" : "Зберегти PNG"}
          </button>

          <button className="share-utility-button" type="button" onClick={shareToTelegram}>
            <Send size={17} /> Telegram
          </button>
          <button className="share-utility-button" type="button" onClick={() => void copy()}>
            {action === "copied" ? <Check size={17} /> : <Copy size={17} />}
            {action === "copying" ? "Копіюємо…" : action === "copied" ? "Скопійовано" : "Скопіювати"}
          </button>
        </div>
      </section>
    </div>,
    document.body,
  );
}
