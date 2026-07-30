"use client";

import { useEffect } from "react";

import { initTheme, useThemeStore } from "@/lib/theme-store";

const OPTIONS: { value: "light" | "dark" | "system"; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];

export function ThemeToggle() {
  const { preference, setPreference } = useThemeStore();

  useEffect(() => {
    initTheme();
  }, []);

  return (
    <div className="flex items-center gap-1 rounded-md border border-border bg-surface p-1 text-sm">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => setPreference(opt.value)}
          className={`rounded px-2 py-1 transition-colors ${
            preference === opt.value
              ? "bg-surface-2 text-primary"
              : "text-secondary hover:text-primary"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
