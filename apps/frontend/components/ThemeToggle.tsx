"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark" | "system";

function systemPrefersDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  const resolved = theme === "system" ? (systemPrefersDark() ? "dark" : "light") : theme;
  document.documentElement.classList.toggle("dark", resolved === "dark");
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem("ai-tutor:theme", theme);
  } catch {}
}

/** Premium theme switcher: light / dark / system. */
export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("system");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = (localStorage.getItem("ai-tutor:theme") as Theme | null) ?? "system";
    setTheme(saved);
    applyTheme(saved);
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = () => {
      const current = (localStorage.getItem("ai-tutor:theme") as Theme | null) ?? "system";
      if (current === "system") applyTheme("system");
    };
    mq.addEventListener?.("change", listener);
    return () => mq.removeEventListener?.("change", listener);
  }, []);

  function nextTheme(): Theme {
    if (theme === "system") return "dark";
    if (theme === "dark") return "light";
    return "system";
  }

  function toggle() {
    const next = nextTheme();
    setTheme(next);
    applyTheme(next);
  }

  const label = theme === "system" ? "🌓 Авто" : theme === "dark" ? "☀️ Светлая" : "🌙 Тёмная";

  return (
    <button
      type="button"
      onClick={mounted ? toggle : undefined}
      aria-label="Переключить тему"
      data-testid="theme-toggle"
      className="rounded-full border border-white/20 bg-white/80 px-3 py-2 text-xs font-black text-[#171022] shadow-glow backdrop-blur hover:bg-white dark:bg-[#181033]/85 dark:text-white"
    >
      {mounted ? label : "…"}
    </button>
  );
}
