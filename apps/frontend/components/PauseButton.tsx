"use client";

/**
 * Sprint 21: Pause button для T1D-ученика.
 *
 * По дизайн-нотам (docs/future/T1D-support-notes.md):
 * "Pause button ('Сделать паузу / у меня гипо'): останавливает время сессии
 *  и НЕ считает streak как прерванный. T1D-friendly."
 *
 * Кнопка:
 * - "Я отойду на 5 минут" — soft pause, time tracked
 * - "У меня гипо/гипер" — hard pause, doesn't count as broken
 * - Возврат → продолжает сессию, streak сохранён
 *
 * UX:
 * - 48px button (T1D слабая моторика)
 * - "Твоя сессия сохранена. Возвращайся когда будешь готов." — НЕ давит
 */

import { useState } from "react";

type PauseReason = "break" | "hypo" | "hyper" | "other" | null;

interface PauseButtonProps {
  /** Callback после выбора причины. Можно использовать для записи в analytics. */
  onPause?: (reason: Exclude<PauseReason, null>) => void;
  /** Показывать кнопку? false = скрыть (например для не-студентов). */
  enabled?: boolean;
}

export default function PauseButton({ onPause, enabled = true }: PauseButtonProps) {
  const [isPaused, setIsPaused] = useState(false);
  const [showOptions, setShowOptions] = useState(false);

  if (!enabled) return null;

  // Sprint 21: T1D-friendly цвета — тёплые, не агрессивные.
  if (isPaused) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="rounded-2xl border-2 border-sky-200 bg-sky-50 p-6 text-center"
      >
        <div className="text-3xl mb-2" aria-hidden="true">
          🌿
        </div>
        <p className="text-sky-900 font-medium text-lg mb-2">
          Твоя сессия сохранена
        </p>
        <p className="text-sky-700 text-sm mb-4 leading-relaxed">
          Возвращайся когда будешь готов. Streak не сломается, сессия
          продолжится с того же места.
        </p>
        <button
          onClick={() => setIsPaused(false)}
          className="min-h-[48px] px-6 py-3 bg-sky-600 text-white rounded-lg font-medium hover:bg-sky-700 transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-sky-500"
        >
          Я вернулся
        </button>
      </div>
    );
  }

  if (showOptions) {
    return (
      <div
        role="dialog"
        aria-labelledby="pause-title"
        className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
      >
        <p id="pause-title" className="text-slate-900 font-medium mb-3">
          Что случилось?
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <button
            onClick={() => {
              onPause?.("break");
              setIsPaused(true);
              setShowOptions(false);
            }}
            className="min-h-[48px] px-4 py-3 bg-white text-slate-900 rounded-lg border border-slate-200 hover:bg-slate-50 text-left transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-sky-500"
          >
            <div className="font-medium">🚶 Отойду на 5 минут</div>
            <div className="text-xs text-slate-500">Сессия сохранится</div>
          </button>
          <button
            onClick={() => {
              onPause?.("hypo");
              setIsPaused(true);
              setShowOptions(false);
            }}
            className="min-h-[48px] px-4 py-3 bg-white text-slate-900 rounded-lg border border-slate-200 hover:bg-slate-50 text-left transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-sky-500"
          >
            <div className="font-medium">🍬 У меня гипо/гипер</div>
            <div className="text-xs text-slate-500">
              Streak не прервётся
            </div>
          </button>
          <button
            onClick={() => {
              onPause?.("other");
              setIsPaused(true);
              setShowOptions(false);
            }}
            className="min-h-[48px] px-4 py-3 bg-white text-slate-900 rounded-lg border border-slate-200 hover:bg-slate-50 text-left transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-sky-500 sm:col-span-2"
          >
            <div className="font-medium">⏸ Другое</div>
            <div className="text-xs text-slate-500">Вернусь позже</div>
          </button>
        </div>
        <button
          onClick={() => setShowOptions(false)}
          className="mt-3 text-sm text-slate-500 hover:text-slate-700"
        >
          Отмена
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => setShowOptions(true)}
      className="min-h-[48px] px-4 py-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors text-sm focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-sky-500"
      aria-label="Сделать паузу в занятии"
    >
      ⏸ Сделать паузу
    </button>
  );
}