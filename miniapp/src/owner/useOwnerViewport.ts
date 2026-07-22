import { useEffect } from "react";

const KEYBOARD_THRESHOLD = 120;

export function useOwnerViewport(): void {
  useEffect(() => {
    const root = document.documentElement;
    const body = document.body;
    const viewport = window.visualViewport;
    let lastWidth = viewport?.width ?? window.innerWidth;
    let maximumHeight = Math.max(window.innerHeight, viewport?.height ?? 0);

    const updateViewport = () => {
      const visibleHeight = viewport?.height ?? window.innerHeight;
      const visibleWidth = viewport?.width ?? window.innerWidth;
      const offsetTop = viewport?.offsetTop ?? 0;

      if (Math.abs(visibleWidth - lastWidth) > 40) {
        lastWidth = visibleWidth;
        maximumHeight = Math.max(window.innerHeight, visibleHeight);
      } else {
        maximumHeight = Math.max(maximumHeight, window.innerHeight, visibleHeight);
      }

      const keyboardInset = Math.max(0, maximumHeight - visibleHeight - offsetTop);
      root.style.setProperty("--owner-viewport-height", `${Math.round(visibleHeight)}px`);
      root.style.setProperty("--owner-viewport-offset-top", `${Math.round(offsetTop)}px`);
      root.style.setProperty("--owner-keyboard-inset", `${Math.round(keyboardInset)}px`);
      body.classList.toggle("owner-keyboard-open", keyboardInset > KEYBOARD_THRESHOLD);
    };

    updateViewport();
    window.addEventListener("resize", updateViewport);
    viewport?.addEventListener("resize", updateViewport);
    viewport?.addEventListener("scroll", updateViewport);

    return () => {
      window.removeEventListener("resize", updateViewport);
      viewport?.removeEventListener("resize", updateViewport);
      viewport?.removeEventListener("scroll", updateViewport);
      body.classList.remove("owner-keyboard-open");
      root.style.removeProperty("--owner-viewport-height");
      root.style.removeProperty("--owner-viewport-offset-top");
      root.style.removeProperty("--owner-keyboard-inset");
    };
  }, []);
}
