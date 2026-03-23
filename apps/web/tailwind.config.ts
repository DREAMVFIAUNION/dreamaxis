import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "../../packages/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        graphite: "#111111",
        panel: "#171717",
        panelRaised: "#202020",
        panelMuted: "#262626",
        ink: "#f5f5f5",
        mutedInk: "#9ca3af",
        signal: "#00d4ff",
        signalSoft: "#a8e8ff",
        warning: "#f7c66a",
        danger: "#f38ba8",
        success: "#4ade80",
      },
      boxShadow: {
        panel: "0 0 0 1px rgba(255,255,255,0.06), 0 24px 60px rgba(0,0,0,0.45)",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
        headline: ["Space Grotesk", "Inter", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
