import { Activity, Crown, MessageCircleMore, Radio, Users } from "lucide-react";
import type { OwnerOverviewData } from "./types";

interface OwnerOverviewProps {
  data: OwnerOverviewData;
}

export function OwnerOverview({ data }: OwnerOverviewProps) {
  const cards = [
    { label: "Користувачів", value: data.users_total, icon: Users, note: "всього профілів" },
    { label: "VIP-клієнтів", value: data.vip_total, icon: Crown, note: "активний premium" },
    { label: "Груп", value: data.groups_total, icon: Radio, note: `${data.active_groups} активних` },
    { label: "Повідомлень", value: data.messages_7d, icon: MessageCircleMore, note: "за останні 7 днів" },
  ];

  return (
    <div className="owner-page">
      <header className="owner-page-heading">
        <div>
          <p>Система під контролем</p>
          <h2>Головний огляд</h2>
        </div>
        <span><Activity size={20} /></span>
      </header>

      <section className="owner-metric-grid">
        {cards.map(({ label, value, icon: Icon, note }) => (
          <article className="owner-metric-card" key={label}>
            <span><Icon size={18} /></span>
            <small>{label}</small>
            <strong>{value.toLocaleString("uk-UA")}</strong>
            <p>{note}</p>
          </article>
        ))}
      </section>

      <section className="owner-panel owner-security-panel">
        <div className="owner-section-title">
          <div>
            <p>Security boundary</p>
            <h3>Захист власника</h3>
          </div>
          <span className="owner-status-dot">LIVE</span>
        </div>
        <div className="owner-check-list">
          <div><i>01</i><span>Telegram initData перевіряється сервером на кожному запиті.</span></div>
          <div><i>02</i><span>Роль прив’язана до незмінного Telegram ID, а не username.</span></div>
          <div><i>03</i><span>VIP не має доступу до цієї панелі та не може видавати ролі.</span></div>
          <div><i>04</i><span>Кожна керувальна дія зберігається в журналі аудиту.</span></div>
        </div>
      </section>
    </div>
  );
}
