import { Check, Crown, RefreshCw, X } from "lucide-react";
import type { VipPlan } from "../vip/types";

interface VipConfirmSheetProps {
  plan: VipPlan | null;
  busy: boolean;
  onCancel(): void;
  onConfirm(plan: VipPlan): void;
}

export function VipConfirmSheet({ plan, busy, onCancel, onConfirm }: VipConfirmSheetProps) {
  if (!plan) return null;
  return (
    <div className="vip-sheet-backdrop" role="presentation" onClick={busy ? undefined : onCancel}>
      <section className="vip-confirm-sheet" role="dialog" aria-modal="true" aria-label="Підтвердження VIP">
        <button type="button" className="vip-confirm-sheet__close" aria-label="Закрити" disabled={busy} onClick={onCancel}>
          <X size={19} />
        </button>
        <span className="vip-confirm-sheet__icon"><Crown size={24} /></span>
        <p>ПІДТВЕРДЖЕННЯ</p>
        <h2>{plan.title}</h2>
        <strong>{plan.stars} ⭐</strong>
        <div className="vip-confirm-sheet__details">
          <span><Check size={15} /> {plan.duration_days} днів повного VIP</span>
          <span><Check size={15} /> {plan.recurring ? "Автопродовження кожні 30 днів" : "Без автоматичного продовження"}</span>
          <span><Check size={15} /> VIP не впливає на XP та рейтинг</span>
        </div>
        <button type="button" className="vip-confirm-sheet__pay" disabled={busy} onClick={() => onConfirm(plan)}>
          {busy ? <RefreshCw className="spin" size={17} /> : <Crown size={17} />}
          Оплатити {plan.stars} ⭐
        </button>
      </section>
    </div>
  );
}
