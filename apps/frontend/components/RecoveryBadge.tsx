"use client";

/**
 * Sprint 42: RecoveryBadge — T1D-friendly indicator.
 *
 * Luna Pro safety:
 * - НЕ интерпретирует glucose data.
 * - НЕ рекомендует specific medical actions.
 * - ТОЛЬКО display: "Recovery mode" если недавно была hypo/hyper пауза.
 * - opt-in: показывается только при `recovery_mode=true` от backend.
 *
 * UX:
 * - Sky/blue calm colors (T1D-friendly).
 * - aria-live=polite (не агрессивный).
 * - Encouragement message: "Возьми лёгкую тему, не торопись".
 */

interface RecoveryBadgeProps {
  recovery: {
    recovery_mode: boolean;
    recovery_reason: string | null;
    minutes_since_pause: number | null;
  } | null;
}

export default function RecoveryBadge({ recovery }: RecoveryBadgeProps) {
  if (!recovery?.recovery_mode) return null;

  const reason = recovery.recovery_reason;
  const minutes = recovery.minutes_since_pause ?? 0;

  return (
    <div
      role="status"
      aria-live="polite"
      className="rounded-2xl border border-sky-200 bg-sky-50 p-3 mb-4 flex items-start gap-3"
      data-testid="recovery-badge"
    >
      <div className="text-xl flex-shrink-0" aria-hidden="true">
        🛌
      </div>
      <div className="flex-1 text-sm">
        <div className="text-sky-900 font-medium">
          Recovery mode
        </div>
        <div className="text-sky-700 mt-1">
          {reason === "recent_hypo" || reason === "recent_hyper"
            ? "Возьми лёгкую тему. Мозг восстанавливается — не торопись."
            : "Возьми лёгкую тему, отдохни."}
        </div>
        {minutes > 0 && (
          <div className="text-sky-600 text-xs mt-1">
            {minutes} мин назад
          </div>
        )}
      </div>
    </div>
  );
}
