import { Crown, LockKeyhole, Sparkles } from "lucide-react";

interface VipUpgradeCardProps {
  title: string;
  description: string;
  source: string;
  featureKey?: string | null;
  trialAvailable?: boolean;
  preview?: React.ReactNode;
  onOpen?(source: string, featureKey?: string | null): void;
}

export function VipUpgradeCard({
  title,
  description,
  source,
  featureKey,
  trialAvailable = false,
  preview,
  onOpen,
}: VipUpgradeCardProps) {
  const open = () => {
    if (onOpen) {
      onOpen(source, featureKey);
      return;
    }
    const params = new URLSearchParams({ source });
    if (featureKey) params.set("feature", featureKey);
    window.location.assign(`/miniapp/vip?${params.toString()}`);
  };

  return (
    <section className="vip-upgrade-card">
      {preview ? <div className="vip-upgrade-card__preview">{preview}</div> : null}
      <div className="vip-upgrade-card__lock"><LockKeyhole size={18} /></div>
      <div className="vip-upgrade-card__copy">
        <p><Sparkles size={13} /> Доступно у VIP</p>
        <h3>{title}</h3>
        <span>{description}</span>
        {trialAvailable ? <em>7 днів за 1 ⭐</em> : null}
      </div>
      <button type="button" onClick={open}>
        <Crown size={16} /> Відкрити VIP
      </button>
    </section>
  );
}
