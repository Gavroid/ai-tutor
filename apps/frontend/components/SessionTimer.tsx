"use client";

/**
 * Sprint 21: SessionTimer — мягкое предупреждение после 20 минут в чате.
 *
 * По дизайн-нотам (docs/future/T1D-support-notes.md):
 * "Glucose-aware session warning: если урок затянулся (>20 мин) — мягкий
 *  prompt 'Ты давно занимаешься, сделай перерыв'."
 *
 * UX:
 * - НЕ блокирует, НЕ давит
 * - 48px кнопки (T1D моторика)
 * - "Спасибо, я заметил" (без слежения)
 * - aria-live="polite" — screen reader узнает о сообщении
 *
 * NOT medical: не интерпретирует glucose. Просто timing-based предупреждение.
 */

import { useEffect, useState } from "react";

interface SessionTimerProps {
  /** Через сколько минут показывать (default 20). */
  thresholdMinutes?: number;
  /** Optional callback при показе предупреждения. */
  onWarn?: () => void;
}

export default function SessionTimer({
  thresholdMinutes = 20,
  onWarn,
}: SessionTimerProps) {
  const [minutesElapsed, setMinutesElapsed] = useState(0);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = (Date.now() - startTime) / 60000;
      setMinutesElapsed(elapsed);
    }, 60000); // обновляем каждую минуту
    return () => clearInterval(interval);
  }, []);

  // Показываем только один раз (после dismissed — не показывать снова).
  const shouldWarn = minutesElapsed >= thresholdMinutes && !dismissed;

  useEffect(() => {
    if (shouldWarn) {
      onWarn?.();
    }
  }, [shouldWarn, onWarn]);

  if (!shouldWarn) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="rounded-2xl border-2 border-amber-200 bg-amber-50 p-4 mb-4"
    >
      <div className="flex items-start gap-3">
        <div className="text-2xl flex-shrink-0" aria-hidden="true">
          ☕
        </div>
        <div className="flex-1">
          <p className="text-amber-900 font-medium mb-1">
            Ты занимаешься уже {Math.floor(minutesElapsed)} минут
          </p>
          <p className="text-amber-800 text-sm mb-3 leading-relaxed">
            Не забывай делать перерывы. Можешь отдохнуть, попить воды или
            перекусить. Твоя сессия сохранится.
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <button
              onClick={() => setDismissed(true)}
              className="min-h-[48px] px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-amber-500"
            >
              Спасибо, я заметил
            </button>
            <button
              onClick={() => setDismissed(true)}
              className="min-h-[48px] px-4 py-2 bg-white text-amber-700 rounded-lg border border-amber-200 text-sm font-medium hover:bg-amber-50 transition-colors focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-amber-500"
            >
              Продолжить
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}