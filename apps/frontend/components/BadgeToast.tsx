"use client";

import { useEffect, useState } from "react";

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
 * Показывает стек карточек (одна за другой если бейджей несколько).
 * Появляется в правом нижнем углу, исчезает через durationMs.
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
      className="fixed bottom-4 right-4 z-50 max-w-[min(92vw,360px)] animate-[badge-toast-in_220ms_ease-out]"
    >
      <div className="prism-card pad border border-emerald-400/40 bg-gradient-to-br from-emerald-500/20 via-[color:var(--prism-panel-solid)] to-[color:var(--prism-panel-solid)] shadow-[0_20px_60px_-15px_rgba(16,185,129,0.4)]">
        <div className="flex items-start gap-3">
          <span aria-hidden className="text-3xl leading-none">
            🎉
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-[10px] font-black uppercase tracking-[0.18em] text-emerald-300">
              Новый бейдж!
            </div>
            <div className="mt-1 space-y-1.5">
              {badges.slice(0, 3).map((b) => (
                <div key={b.slug} className="flex items-center gap-2">
                  <span aria-hidden className="text-2xl leading-none">
                    {b.icon}
                  </span>
                  <div className="min-w-0">
                    <div className="truncate text-sm font-black text-[color:var(--prism-ink)]">
                      {b.title}
                    </div>
                    {b.description && (
                      <div className="truncate text-[11px] text-[color:var(--prism-muted)]">
                        {b.description}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {badges.length > 3 && (
                <div className="text-xs text-[color:var(--prism-muted)]">
                  и ещё {badges.length - 3}...
                </div>
              )}
            </div>
            <a
              href="/student/badges"
              className="mt-2 inline-block text-[11px] font-black uppercase tracking-[0.14em] text-emerald-300 hover:text-emerald-200"
            >
              Все достижения →
            </a>
          </div>
          <button
            type="button"
            onClick={() => {
              setVisible(false);
              onDismiss?.();
            }}
            aria-label="Закрыть"
            className="shrink-0 rounded p-1 text-[color:var(--prism-muted)] hover:text-[color:var(--prism-ink)]"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
}
