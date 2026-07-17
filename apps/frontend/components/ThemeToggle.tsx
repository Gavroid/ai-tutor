"use client";

import { useEffect, useState } from "react";

/**
 * Sprint 5.3 — переключатель темы (светлая / тёмная).
 * Хранит выбор в localStorage + применяет class="dark" на <html>.
 */
export default function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = (typeof window !== "undefined" && localStorage.getItem("ai-tutor:theme")) as
      | "light"
      | "dark"
      | null;
    const initial: "light" | "dark" =
      saved ??
      (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    setTheme(initial);
    applyTheme(initial);
  }, []);

  function applyTheme(t: "light" | "dark") {
    if (typeof document !== "undefined") {
      document.documentElement.classList.toggle("dark", t === "dark");
    }
    try {
      localStorage.setItem("ai-tutor:theme", t);
    } catch {
      // localStorage может быть недоступен (приватный режим).
    }
  }

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    applyTheme(next);
  }

  // До mount избегаем рендера чтобы не было flicker (light->dark jump).
  if (!mounted) {
    return (
      <button
        type="button"
        aria-label="Переключить тему"
        className="rounded-md bg-slate-200 px-3 py-1 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-500"
      >
        …
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="Переключить тему"
      data-testid="theme-toggle"
      className="rounded-md bg-slate-200 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
    >
      {theme === "dark" ? "☀️ Светлая" : "🌙 Тёмная"}
    </button>
  );
}