import { create } from "zustand";

export type ThemePreference = "light" | "dark" | "system";

interface ThemeState {
  preference: ThemePreference;
  setPreference: (pref: ThemePreference) => void;
}

function applyTheme(pref: ThemePreference) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (pref === "system") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", pref);
  }
  window.localStorage.setItem("clusius-theme", pref);
}

export const useThemeStore = create<ThemeState>((set) => ({
  preference: "system",
  setPreference: (preference) => {
    applyTheme(preference);
    set({ preference });
  },
}));

export function initTheme() {
  if (typeof window === "undefined") return;
  const stored = window.localStorage.getItem("clusius-theme") as ThemePreference | null;
  if (stored) {
    applyTheme(stored);
    useThemeStore.setState({ preference: stored });
  }
}
