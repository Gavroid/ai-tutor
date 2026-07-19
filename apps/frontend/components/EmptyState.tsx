"use client";

interface EmptyStateProps {
  /** Иконка (emoji или SVG string). По умолчанию — 📭 */
  icon?: string;
  /** Заголовок (крупно). */
  title: string;
  /** Пояснение под заголовком (опционально). */
  description?: string;
  /** Ссылка-CTA (опционально) — например, к действию. */
  action?: { label: string; href?: string; onClick?: () => void };
  /** Sprint 11.3: контекст для сообщения ('positive' = молодец, 'neutral' = нет данных, 'loading' = спиннер). */
  variant?: "neutral" | "positive" | "loading";
}

/**
 * Sprint 11.3 — единый компонент empty state для всех страниц.
 *
 * T1D-friendly: кнопка-CTA крупная (44x44 min), контрастная.
 * Используется на /parents, /teacher/*, /admin (badges/users),
 * когда данных нет.
 */
export default function EmptyState({
  icon = "📭",
  title,
  description,
  action,
  variant = "neutral",
}: EmptyStateProps) {
  const bgClass =
    variant === "positive"
      ? "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800"
      : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700";

  return (
    <div
      data-testid="empty-state"
      role="status"
      aria-live="polite"
      className={`rounded-2xl border-2 border-dashed p-10 text-center ${bgClass}`}
    >
      <div className="text-5xl" aria-hidden="true">
        {icon}
      </div>
      <h3 className="mt-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
        {title}
      </h3>
      {description && (
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          {description}
        </p>
      )}
      {action && (
        <div className="mt-6 flex justify-center">
          {action.href ? (
            <a
              href={action.href}
              className="inline-flex items-center rounded-lg bg-sky-600 px-6 py-3 text-base font-semibold text-white shadow hover:bg-sky-500"
            >
              {action.label}
            </a>
          ) : (
            <button
              type="button"
              onClick={action.onClick}
              className="inline-flex items-center rounded-lg bg-sky-600 px-6 py-3 text-base font-semibold text-white shadow hover:bg-sky-500"
            >
              {action.label}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
