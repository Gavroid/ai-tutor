/**
 * Sprint 41: i18n — простой helper для переводов.
 *
 * Стратегия: client-side only (YAGNI для SSR i18n).
 * - localStorage 'locale' для persistence
 * - Default: 'ru' (текущий основной язык)
 * - Fallback: 'ru' если ключ не найден в выбранном языке
 */

import { useEffect, useState } from "react";
import ru from "@/messages/ru.json";
import en from "@/messages/en.json";

export type Locale = "ru" | "en";

const messages: Record<Locale, Record<string, string>> = { ru, en };

const STORAGE_KEY = "ai-tutor:locale";

/** Определяет начальный locale (localStorage > navigator > default 'ru'). */
function detectInitialLocale(): Locale {
  if (typeof window === "undefined") return "ru";
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "ru" || stored === "en") return stored;
  const browser = navigator.language.toLowerCase();
  if (browser.startsWith("en")) return "en";
  return "ru";
}

/** Sync t() function — для non-React contexts (rare). */
export function tSync(key: string, locale: Locale = "ru", vars?: Record<string, string | number>): string {
  const dict = messages[locale] || messages.ru;
  let text = dict[key] || messages.ru[key] || key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      text = text.replace(`{${k}}`, String(v));
    }
  }
  return text;
}

/** React hook для t() + locale switching. */
export function useLocale() {
  const [locale, setLocaleState] = useState<Locale>("ru");

  useEffect(() => {
    setLocaleState(detectInitialLocale());
  }, []);

  function setLocale(newLocale: Locale) {
    setLocaleState(newLocale);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, newLocale);
    }
  }

  function t(key: string, vars?: Record<string, string | number>): string {
    return tSync(key, locale, vars);
  }

  return { locale, setLocale, t };
}