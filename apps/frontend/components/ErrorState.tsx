"use client";

import { useState } from "react";

interface ErrorStateProps {
  /** Sprint 12 — T1D-friendly error UI.
   *
   * Использование:
   *   - AI endpoint упал/timeout (503/504)
   *   - Network error (offline)
   *   - Generic backend error (5xx)
   *
   * Что НЕ должно быть:
   *   - Жёлтые error banners которые отвлекают (T1D — легко отвлечься)
   *   - Stack traces
   *   - Громоздкие сообщения
   *
   * T1D-friendly: ошибка должна быть спокойной, support-кнопкой retry
   * (без резких перезагрузок), объяснить что делать дальше простыми словами.
   */
  variant?: "network" | "ai" | "generic";
  title?: string;
  description?: string;
  onRetry?: () => void | Promise<void>;
  /** Полный текст ошибки — скрыт по умолчанию, можно развернуть. */
  error?: string;
}

const VARIANTS = {
  network: {
    icon: "📡",
    title: "Нет связи с сервером",
    description:
      "Проверь интернет или Wi-Fi. Когда связь появится — попробуй ещё раз.",
    bgClass:
      "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800",
  },
  ai: {
    icon: "🤖",
    title: "AI временно недоступен",
    description:
      "Нейросеть перегружена или отвечает слишком долго. Попробуй позже.",
    bgClass:
      "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700",
  },
  generic: {
    icon: "⚠️",
    title: "Что-то пошло не так",
    description: "Попробуй обновить страницу или повторить действие.",
    bgClass:
      "bg-rose-50 dark:bg-rose-900/20 border-rose-200 dark:border-rose-800",
  },
} as const;

export default function ErrorState({
  variant = "generic",
  title,
  description,
  onRetry,
  error,
}: ErrorStateProps) {
  const cfg = VARIANTS[variant];
  const finalTitle = title ?? cfg.title;
  const finalDesc = description ?? cfg.description;
  const [showDetails, setShowDetails] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  async function handleRetry() {
    if (!onRetry) return;
    setIsRetrying(true);
    try {
      await onRetry();
    } finally {
      // Не снимаем isRetrying сразу — родительский компонент покажет данные
      // и перестанет показывать ErrorState. Timeout на 15 сек — страховка.
      setTimeout(() => setIsRetrying(false), 15_000);
    }
  }

  return (
    <div
      data-testid="error-state"
      role="alert"
      aria-live="polite"
      className={`rounded-2xl border-2 p-6 ${cfg.bgClass}`}
    >
      <div className="flex items-start gap-3">
        <div className="text-3xl" aria-hidden="true">
          {cfg.icon}
        </div>
        <div className="flex-1">
          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            {finalTitle}
          </h3>
          <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">
            {finalDesc}
          </p>
          {error && (
            <button
              onClick={() => setShowDetails((v) => !v)}
              className="mt-2 text-xs text-slate-500 underline hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            >
              {showDetails ? "Скрыть" : "Подробности"}
            </button>
          )}
          {error && showDetails && (
            <pre className="mt-2 overflow-x-auto rounded bg-slate-100 p-2 text-xs text-slate-700 dark:bg-slate-900 dark:text-slate-300">
              {error}
            </pre>
          )}
          <div className="mt-3 flex gap-2">
            {onRetry && (
              <button
                type="button"
                onClick={handleRetry}
                disabled={isRetrying}
                className="inline-flex items-center rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-sky-500 disabled:opacity-60"
              >
                {isRetrying ? "Пробую снова…" : "Попробовать ещё раз"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
