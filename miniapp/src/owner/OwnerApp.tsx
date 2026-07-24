import { AlertTriangle, Crown, LockKeyhole } from "lucide-react";
import { appPaths } from "../routing/paths";
import { isTelegramContext } from "../telegram/sdk";
import { useOwnerWorkspace } from "./hooks/useOwnerWorkspace";
import { OwnerRoutes } from "./OwnerRoutes";
import { OwnerShell } from "./OwnerShell";
import "./styles";

export function OwnerApp() {
  const workspace = useOwnerWorkspace();
  if (!isTelegramContext()) return <main className="owner-gate"><LockKeyhole size={34} /><h1>Відкрий Owner Panel через Telegram</h1><p>Захищена авторизація працює лише через підписану Telegram Mini App session.</p></main>;
  if (workspace.loading) return <main className="owner-gate owner-gate--loading"><Crown size={34} /><h1>Owner Control</h1><p>Перевіряємо захищений доступ…</p><div className="owner-loader"><span /></div></main>;
  if (workspace.forbidden || !workspace.session) return <main className="owner-gate owner-gate--danger"><LockKeyhole size={34} /><h1>Owner Panel закрито</h1><p>{workspace.error || "Цей маршрут доступний лише команді ChatPulse."}</p><button type="button" onClick={() => workspace.navigate(appPaths.home)}>Повернутися в ChatPulse</button></main>;
  return <OwnerShell session={workspace.session} activeTab={workspace.activeTab} onTabChange={workspace.navigateTab} busy={workspace.busy}>
    {workspace.error ? <button type="button" className="owner-error-banner" onClick={() => workspace.setError("")}><AlertTriangle size={16} /> {workspace.error}</button> : null}
    <OwnerRoutes workspace={workspace} />
  </OwnerShell>;
}
