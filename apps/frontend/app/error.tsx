"use client";

/**
 * Sprint 16.2 P2-5 + Sprint 3.7 polish: Next.js error boundary для
 * неперехваченных React exceptions.
 *
 * T1D-friendly:
 * - Спокойное сообщение без давления ("что-то пошло не так")
 * - Кнопка "Попробовать снова" (retry)
 * - Кнопка "На главную" (не вынуждает user решать проблему)
 * - Можно скопировать ID ошибки + последние crash-события в поддержку
 *
 * Если ошибка произошла во время T1D-эпизода (гипо/гипер), user может
 * просто нажать "На главную" — ничего не потеряется.
 *
 * Sprint 3.7 polish:
 * - report(error) → ring buffer в localStorage (см. lib/crash-reporter.ts)
 * - Кнопка "Скопировать диагностику" копирует JSON с последними 20 событиями
 *   (включая это) — родитель или Кирилл могут прислать в поддержку.
 */

import { useEffect, useState } from "react";
import {
  formatCrashesForCopy,
  getRecentCrashes,
  report as reportCrash,
} from "@/lib/crash-reporter";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [copied, setCopied] = useState<"idle" | "ok" | "fail">("idle");

  useEffect(() => {
    // console — для debugging в devtools.
    console.error("Unhandled error:", error);
    // Ring buffer в localStorage (Sprint 3.7 polish).
    reportCrash(error, { kind: "boundary", digest: error.digest });
  }, [error]);

  async function copyDiagnostics() {
    const text = formatCrashesForCopy();
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback для старых iOS Safari (нет clipboard API на http://).
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        const ok = document.execCommand("copy");
        document.body.removeChild(ta);
        if (!ok) throw new Error("execCommand copy failed");
      }
      setCopied("ok");
      setTimeout(() => setCopied("idle"), 2500);
    } catch {
      setCopied("fail");
      setTimeout(() => setCopied("idle"), 3500);
    }
  }

  const recentCount = getRecentCrashes().length;

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

        <h1 className="text-2xl font-bold text-[color:var(--prism-ink)] mb-3">
          Что-то пошло не так
        </h1>

        <p className="text-[color:var(--prism-muted)] mb-2 leading-relaxed">
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
            className="min-h-[48px] px-6 py-3 bg-slate-200 text-[color:var(--prism-ink)] rounded-lg font-medium hover:bg-slate-300 transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-slate-400 inline-flex items-center justify-center"
          >
            На главную
          </a>
        </div>

        {/* Sprint 3.7: copy diagnostics — последние {recentCount} событий. */}
        {recentCount > 0 && (
          <div className="mt-6 flex flex-col items-center gap-2">
            <button
              type="button"
              onClick={copyDiagnostics}
              className="min-h-[40px] px-4 py-2 bg-slate-100 text-slate-700 text-sm rounded-md font-medium hover:bg-slate-200 transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-slate-400 inline-flex items-center gap-2"
              data-testid="crash-copy-btn"
            >
              {copied === "ok"
                ? "✅ Скопировано"
                : copied === "fail"
                  ? "⚠️ Не вышло — покажи код поддержке"
                  : `📋 Скопировать диагностику (${recentCount})`}
            </button>
            <p className="text-xs text-slate-400">
              В поддержку: вставь JSON из буфера вместе с кодом ошибки.
            </p>
          </div>
        )}

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
