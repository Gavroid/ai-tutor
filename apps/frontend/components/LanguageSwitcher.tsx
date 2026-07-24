"use client";

/**
 * Sprint 41: LanguageSwitcher.
 *
 * Простая кнопка RU ↔ EN, persists в localStorage.
 */

import { useLocale } from "@/lib/i18n";

export default function LanguageSwitcher() {
  const { locale, setLocale } = useLocale();

  function toggle() {
    setLocale(locale === "ru" ? "en" : "ru");
  }

  return (
    <button
      type="button"
      onClick={toggle}
      data-testid="language-switcher"
      aria-label="Switch language"
      className="rounded-md bg-slate-200 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-sky-500"
    >
      {locale === "ru" ? "EN" : "RU"}
    </button>
  );
}