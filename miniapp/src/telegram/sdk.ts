type HapticType = "light" | "medium" | "heavy";

interface TelegramWebApp {
  initData: string;
  colorScheme?: "light" | "dark";
  themeParams?: Record<string, string>;
  ready(): void;
  expand(): void;
  close(): void;
  setHeaderColor?(color: string): void;
  setBackgroundColor?(color: string): void;
  BackButton?: {
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
  };
  HapticFeedback?: {
    impactOccurred(type: HapticType): void;
    notificationOccurred(type: "error" | "success" | "warning"): void;
  };
  openTelegramLink?(url: string): void;
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

export const telegram = window.Telegram?.WebApp;

export function initTelegram(): void {
  if (!telegram) return;
  telegram.ready();
  telegram.expand();
  telegram.setHeaderColor?.("#090b12");
  telegram.setBackgroundColor?.("#090b12");
}

export function getInitData(): string {
  return telegram?.initData ?? "";
}

export function isTelegramContext(): boolean {
  return Boolean(getInitData()) || import.meta.env.MODE === "test" || import.meta.env.DEV;
}

export function haptic(type: HapticType = "light"): void {
  telegram?.HapticFeedback?.impactOccurred(type);
}

export function notify(type: "error" | "success" | "warning"): void {
  telegram?.HapticFeedback?.notificationOccurred(type);
}

export function openTelegramLink(url: string): void {
  if (telegram?.openTelegramLink) {
    telegram.openTelegramLink(url);
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

export function bindBackButton(callback: (() => void) | null): () => void {
  const button = telegram?.BackButton;
  if (!button || !callback) {
    button?.hide();
    return () => undefined;
  }
  button.show();
  button.onClick(callback);
  return () => {
    button.offClick(callback);
    button.hide();
  };
}
