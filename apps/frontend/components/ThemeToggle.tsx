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
      className={[
        // Sprint 3.9.1: контрастная в обеих темах (раньше была
        // bg-white/80 + dark:bg-[#181033]/85 — в light mode сливалась
        // с белым header).
        // Используем glass-effect: полупрозрачный фон + жирная граница
        // + backdrop-blur → видна поверх любого header.
        "pointer-events-auto",
        "inline-flex items-center gap-1.5",
        "min-h-[36px] px-3 py-2",
        "rounded-full",
        "border-2 border-white/40 dark:border-white/30",
        "bg-slate-900/85 text-white",
        "dark:bg-white/90 dark:text-slate-900",
        "shadow-lg shadow-black/20",
        "backdrop-blur-md",
        "text-xs font-black tracking-wide",
        "transition-colors",
        "hover:bg-slate-900/95 dark:hover:bg-white",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400",
      ].join(" ")}
    >
      {mounted ? label : "…"}
    </button>
  );
}
