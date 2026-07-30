import typography from "@tailwindcss/typography";
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        page: "var(--page)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        primary: "var(--text-primary)",
        secondary: "var(--text-secondary)",
        muted: "var(--text-muted)",
        gridline: "var(--gridline)",
        baseline: "var(--baseline)",
        border: "var(--border)",
        "series-1": "var(--series-1)",
        "series-1-soft": "var(--series-1-soft)",
        "series-2": "var(--series-2)",
        "series-3": "var(--series-3)",
        good: "var(--status-good)",
        warning: "var(--status-warning)",
        serious: "var(--status-serious)",
        critical: "var(--status-critical)",
        "success-text": "var(--success-text)",
      },
    },
  },
  plugins: [typography],
};

export default config;
