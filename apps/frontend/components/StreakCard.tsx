"use client";

interface StreakData {
  current_streak_days: number;
  longest_streak_days: number;
  total_active_days: number;
  last_active_date: string | null;
  encouragement: string;
}

interface StreakCardProps {
  streak: StreakData;
}

/**
 * Sprint 8.1 — карточка streak для ученика.
 *
 * T1D-friendly дизайн:
 * - current_streak показывает текущую серию (обнуляется при пропуске)
 * - longest_streak показывает ЛУЧШУЮ серию за всё время (никогда не уменьшается)
 * - total_active_days = общее количество дней с активностью
 * - Никаких "🔥 STREAK LOST!" сообщений — только поддержка
 */
export default function StreakCard({ streak }: StreakCardProps) {
  const { current_streak_days, longest_streak_days, total_active_days, last_active_date, encouragement } = streak;

  return (
    <div
      data-testid="streak-card"
      className="rounded-2xl border border-slate-200 bg-gradient-to-br from-amber-50 to-rose-50 p-6 shadow-sm dark:border-slate-700 dark:from-amber-900/20 dark:to-rose-900/20"
    >
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">
            🔥 Твоя серия
          </h2>
          <p className="mt-1 text-3xl font-bold text-slate-900 dark:text-slate-100">
            {current_streak_days} {pluralDays(current_streak_days)}
          </p>
        </div>
        <div className="text-right text-xs text-slate-500">
          <div>Лучшая: <strong>{longest_streak_days}</strong></div>
          <div>Всего: <strong>{total_active_days}</strong></div>
          {last_active_date && (
            <div className="mt-1">Последний: {last_active_date}</div>
          )}
        </div>
      </div>

      <p className="mt-4 text-sm text-slate-700 dark:text-slate-300">{encouragement}</p>

      <div className="mt-4 rounded-md bg-white/60 p-2 text-xs text-slate-600 dark:bg-slate-800/60 dark:text-slate-400">
        💡 <strong>Важно:</strong> пропуск дня — это нормально. Ты всегда можешь вернуться.
        Главное — общий прогресс (total_active_days), а не серия.
      </div>
    </div>
  );
}

function pluralDays(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "день";
  if ([2, 3, 4].includes(mod10) && ![12, 13, 14].includes(mod100)) return "дня";
  return "дней";
}