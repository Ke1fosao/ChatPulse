import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const releaseVersion = readFileSync(resolve(import.meta.dirname, "../VERSION"), "utf8").trim();

export default defineConfig({
  plugins: [react()],
  base: "/miniapp/",
  define: {
    __CHATPULSE_VERSION__: JSON.stringify(releaseVersion),
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8080",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
  },
});
