"use client";

import Link from "next/link";

interface NextTopicData {
  topic_id: number | null;
  topic_name: string | null;
  subject_id: number | null;
  subject_name: string | null;
  reason: "weak_topic" | "next_in_curriculum" | "all_mastered";
  mastery_score: number | null;
  encouragement: string;
}

interface NextTopicCardProps {
  next: NextTopicData;
  onRefresh?: () => void;
}

/**
 * Sprint 8.2 — карточка рекомендации следующей темы.
 *
 * 3 варианта reason:
 * - "weak_topic": есть тема с низким mastery — повтори
 * - "next_in_curriculum": следующая непройденная тема
 * - "all_mastered": все темы пройдены — поздравление
 */
export default function NextTopicCard({ next, onRefresh }: NextTopicCardProps) {
  const { topic_id, topic_name, subject_id, subject_name, reason, mastery_score, encouragement } = next;

  if (reason === "all_mastered") {
    return (
      <div
        data-testid="next-topic-card"
        className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50 p-6 shadow-sm dark:border-emerald-700 dark:from-emerald-900/20 dark:to-teal-900/20"
      >
        <div className="flex items-start gap-3">
          <div className="text-3xl">🎉</div>
          <div className="flex-1">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
              Все темы освоены!
            </h2>
            <p className="mt-2 text-base text-slate-800 dark:text-slate-200">{encouragement}</p>
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="mt-3 rounded-md bg-emerald-100 px-3 py-1.5 text-xs font-medium text-emerald-800 hover:bg-emerald-200"
              >
                Обновить
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (!topic_id || !topic_name || !subject_id) {
    return null;
  }

  const isWeak = reason === "weak_topic";

  return (
    <div
      data-testid="next-topic-card"
      className={`rounded-2xl border p-6 shadow-sm ${
        isWeak
          ? "border-rose-200 bg-gradient-to-br from-rose-50 to-amber-50 dark:border-rose-700 dark:from-rose-900/20 dark:to-amber-900/20"
          : "border-sky-200 bg-gradient-to-br from-sky-50 to-indigo-50 dark:border-sky-700 dark:from-sky-900/20 dark:to-indigo-900/20"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
            {isWeak ? "📌 Повтори тему" : "📚 Следующая тема"}
          </h2>
          <p className="mt-2 text-xl font-bold text-slate-900 dark:text-slate-100">{topic_name}</p>
          {subject_name && (
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Предмет: {subject_name}
            </p>
          )}
          {isWeak && mastery_score !== null && (
            <p className="mt-2 inline-block rounded-full bg-rose-100 px-3 py-1 text-xs font-medium text-rose-800 dark:bg-rose-900/40 dark:text-rose-200">
              Текущее освоение: {Math.round(mastery_score * 100)}%
            </p>
          )}
          <p className="mt-3 text-sm text-slate-700 dark:text-slate-300">{encouragement}</p>
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <Link
          href={`/topics/${topic_id}`}
          className="flex-1 rounded-md bg-sky-600 px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-sky-500"
        >
          {isWeak ? "Повторить →" : "Начать →"}
        </Link>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="rounded-md bg-slate-200 px-3 py-2.5 text-xs text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
          >
            🔄
          </button>
        )}
      </div>
    </div>
  );
}