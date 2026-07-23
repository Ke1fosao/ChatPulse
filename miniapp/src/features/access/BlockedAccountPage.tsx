import { Ban, ShieldAlert } from "lucide-react";

interface BlockedAccountPageProps {
  reason?: string | null;
}

export function BlockedAccountPage({ reason }: BlockedAccountPageProps) {
  return (
    <main className="blocked-account-page">
      <div className="blocked-account-page__glow" />
      <span className="blocked-account-page__icon"><Ban size={34} /></span>
      <p>Доступ обмежено</p>
      <h1>Акаунт заблоковано</h1>
      <div className="blocked-account-page__notice">
        <ShieldAlert size={19} />
        <div>
          <strong>ChatPulse недоступний</strong>
          <span>{reason || "Адміністратор обмежив доступ до бота та Mini App."}</span>
        </div>
      </div>
      <small>Для уточнення звернися до підтримки ChatPulse.</small>
    </main>
  );
}
