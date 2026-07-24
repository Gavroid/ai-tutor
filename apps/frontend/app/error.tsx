"use client";

/**
 * Sprint 16.2 P2-5: Next.js error boundary для неперехваченных React exceptions.
 *
 * T1D-friendly:
 * - Спокойное сообщение без давления ("что-то пошло не так")
 * - Кнопка "Попробовать снова" (retry)
 * - Кнопка "На главную" (не вынуждает user решать проблему)
 * - Можно скопировать ID ошибки в поддержку
 *
 * Если ошибка произошла во время T1D-эпизода (гипо/гипер), user может
 * просто нажать "На главную" — ничего не потеряется.
 */

import { useEffect } from "react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Sprint 16.2 P2-5: structured log в консоль для debugging
    // В production: можно подключить Sentry / logrocket здесь
    console.error("Unhandled error:", error);
  }, [error]);

  return (
    <main
      className="flex min-h-screen flex-col items-center justify-center p-6 text-center"
      role="alert"
      aria-live="assertive"
    >
      <div className="max-w-md">
        {/* Иконка — НЕ страшная, нейтральная */}
        <div className="text-6xl mb-4" aria-hidden="true">
          🌿
        </div>

        <h1 className="text-2xl font-bold text-slate-900 mb-3">
          Что-то пошло не так
        </h1>

        <p className="text-slate-700 mb-2 leading-relaxed">
          Не переживай — твои ответы сохранены.
        </p>

        <p className="text-slate-600 text-sm mb-6 leading-relaxed">
          Можешь попробовать ещё раз или вернуться на главную.
          Если ошибка повторяется — покажи её родителям.
        </p>

        {/* Действия — крупные кнопки, легко нажать */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={reset}
            className="min-h-[48px] px-6 py-3 bg-sky-600 text-white rounded-lg font-medium hover:bg-sky-700 transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-sky-500"
          >
            Попробовать снова
          </button>

          <a
            href="/subjects"
            className="min-h-[48px] px-6 py-3 bg-slate-200 text-slate-900 rounded-lg font-medium hover:bg-slate-300 transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-slate-400 inline-flex items-center justify-center"
          >
            На главную
          </a>
        </div>

        {/* Технический ID ошибки — для поддержки */}
        {error.digest && (
          <p className="text-xs text-slate-400 mt-6 font-mono">
            Код ошибки: {error.digest}
          </p>
        )}
      </div>
    </main>
  );
}