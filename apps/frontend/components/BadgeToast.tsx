"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export interface BadgeToastItem {
  slug: string;
  title: string;
  icon: string;
  description?: string;
}

export interface BadgeToastProps {
  /** Список новых бейджей (появляются по одному, стекаются в группу). */
  badges: BadgeToastItem[];
  /** Время показа в мс (по умолчанию 6000 = 6 секунд). */
  durationMs?: number;
  /** Коллбэк когда toast закрывается (для очистки в родителе). */
  onDismiss?: () => void;
}

/**
 * Sprint 3.11 — toast «🎉 Новый бейдж!»
 *
 * Sprint 3.14: размер увеличен, расположение — по центру экрана (overlay),
 * backdrop blur + кнопка-CTA «Все достижения» (крупная, ведёт на /student/badges).
 *
 * T1D-friendly: нет таймера обратного отсчёта, нет давления.
 * Просто позитивное уведомление.
 */
export default function BadgeToast({
  badges,
  durationMs = 6000,
  onDismiss,
}: BadgeToastProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (badges.length === 0) return;
    setVisible(true);
    const timer = setTimeout(() => {
      setVisible(false);
      onDismiss?.();
    }, durationMs);
    return () => clearTimeout(timer);
  }, [badges, durationMs, onDismiss]);

  if (badges.length === 0 || !visible) return null;

  return (
    <div
      data-testid="badge-toast"
      role="status"
      aria-live="polite"
      // Sprint 3.14: overlay на весь экран, центрирование через flex.
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      {/* Backdrop — кликабельный для закрытия. */}
      <button
        type="button"
        aria-label="Закрыть"
        onClick={() => {
          setVisible(false);
          onDismiss?.();
        }}
        className="absolute inset-0 bg-black/40 backdrop-blur-sm cursor-default animate-[badge-toast-backdrop-in_180ms_ease-out]"
      />

      {/* Карточка по центру. */}
      <div
        data-testid="badge-toast-card"
        className="relative w-full max-w-md rounded-3xl border border-emerald-400/40 bg-gradient-to-br from-emerald-500/20 via-[color:var(--prism-panel-solid)] to-[color:var(--prism-panel-solid)] p-6 shadow-[0_30px_80px_-15px_rgba(16,185,129,0.45)] animate-[badge-toast-in_240ms_ease-out]"
      >
        {/* Кнопка закрытия (X) в углу. */}
        <button
          type="button"
          onClick={() => {
            setVisible(false);
            onDismiss?.();
          }}
          aria-label="Закрыть"
          className="absolute right-3 top-3 rounded-full p-1.5 text-[color:var(--prism-muted)] hover:bg-white/10 hover:text-[color:var(--prism-ink)]"
        >
          <span aria-hidden className="text-lg leading-none">✕</span>
        </button>

        {/* Header: 🎉 + kicker. */}
        <div className="flex items-center gap-3">
          <span aria-hidden className="text-5xl leading-none">🎉</span>
          <div>
            <div className="text-xs font-black uppercase tracking-[0.18em] text-emerald-300">
              Новый бейдж!
            </div>
            <div className="mt-0.5 text-xs text-[color:var(--prism-muted)]">
              {badges.length === 1
                ? "Ты только что получил достижение"
                : `Ты получил ${badges.length} новых достижений`}
            </div>
          </div>
        </div>

        {/* Список бейджей. */}
        <div className="mt-5 space-y-3">
          {badges.slice(0, 4).map((b) => (
            <div
              key={b.slug}
              data-testid="badge-toast-item"
              className="flex items-start gap-3 rounded-2xl border border-emerald-400/30 bg-emerald-500/5 p-3"
            >
              <span aria-hidden className="shrink-0 text-3xl leading-none">{b.icon}</span>
              <div className="min-w-0 flex-1">
                <div className="text-base font-black text-[color:var(--prism-ink)]">
                  {b.title}
                </div>
                {b.description && (
                  <div className="mt-0.5 text-sm leading-snug text-[color:var(--prism-muted)]">
                    {b.description}
                  </div>
                )}
              </div>
            </div>
          ))}
          {badges.length > 4 && (
            <div className="text-sm text-[color:var(--prism-muted)] text-center">
              и ещё {badges.length - 4}...
            </div>
          )}
        </div>

        {/* Кнопка-CTA — primary, ведёт на /student/badges (Sprint 3.15: next/link вместо <a> для SPA-навигации). */}
        <Link
          href="/student/badges"
          data-testid="badge-toast-cta"
          className="prism-action primary mt-5 flex w-full items-center justify-center gap-2 px-6 py-3 text-sm font-black uppercase tracking-[0.16em]"
        >
          Все достижения
          <span aria-hidden>→</span>
        </Link>
      </div>
    </div>
  );
}
