"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, ApiError } from "@/lib/api";
import StreakCard from "@/components/StreakCard";
import NextTopicCard from "@/components/NextTopicCard";
import Skeleton from "@/components/Skeleton";
import ErrorState from "@/components/ErrorState";

type BadgeOut = {
  slug: string;
  title: string;
  description: string;
  icon: string;
  awarded_at: string | null;
  evidence: Record<string, unknown>;
};

export default function StudentBadgesClient() {
  const router = useRouter();
  const [badges, setBadges] = useState<BadgeOut[] | null>(null);
  // Sprint 12: error state отдельно от loading. Если network/server
  // упало — показываем ErrorState вместо infinite skeleton.
  const [badgesError, setBadgesError] = useState<string | null>(null);
  const [streak, setStreak] = useState<{
    current_streak_days: number;
    longest_streak_days: number;
    total_active_days: number;
    last_active_date: string | null;
    encouragement: string;
  } | null>(null);
  // Sprint 8.2: рекомендация следующей темы.
  const [nextTopic, setNextTopic] = useState<{
    topic_id: number | null;
    topic_name: string | null;
    subject_id: number | null;
    subject_name: string | null;
    reason: "weak_topic" | "next_in_curriculum" | "all_mastered";
    mastery_score: number | null;
    encouragement: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [newlyAwarded, setNewlyAwarded] = useState<string[]>([]);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    refresh();
    // Sprint 8.1: parallel load streak
    api.studentStreak().then(setStreak).catch(() => {});
    // Sprint 8.2: parallel load next topic
    api.recommendNext().then(setNextTopic).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refresh() {
    setBusy(true);
    setBadgesError(null);
    try {
      const b = await api.studentBadges();
      setBadges(b);
    } catch (err) {
      // Sprint 12: вместо «Загрузка вечно» — фиксируем ошибку и
      // показываем ErrorState с retry.
      setBadgesError(
        err instanceof ApiError
          ? `HTTP ${err.status}: ${err.message}`
          : String(err),
      );
    } finally {
      setBusy(false);
    }
  }

  async function evaluate() {
    setBusy(true);
    try {
      const awarded: string[] = await api.studentBadgesEvaluate();
      setNewlyAwarded(awarded);
      await refresh();
      setTimeout(() => setNewlyAwarded([]), 5000);
    } finally {
      setBusy(false);
    }
  }

  if (badges === null) {
    // Sprint 12: error имеет приоритет над skeleton.
    if (badgesError) {
      return (
        <ErrorState
          variant="generic"
          error={badgesError}
          onRetry={() => refresh()}
        />
      );
    }
    // Sprint 11.4: skeleton вместо "Загрузка..." чтобы избежать
    // визуальных скачков layout и показать что идёт работа.
    return (
      <div data-testid="badges-skeleton" className="space-y-4">
        <div className="rounded-2xl border border-slate-200 p-6 shadow-sm">
          <Skeleton width="w-48" height="h-6" />
          <Skeleton className="mt-3" width="w-72" height="h-4" />
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <Skeleton width="w-12" height="h-12" className="rounded-full" />
              <Skeleton className="mt-3" width="w-full" />
              <Skeleton className="mt-2" width="w-3/4" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const earned = badges.filter((b) => b.awarded_at);
  const locked = badges.filter((b) => !b.awarded_at);

  return (
    <div>
      {/* Sprint 8.1: streak card (T1D-friendly) */}
      {streak && (
        <div className="mt-4">
          <StreakCard streak={streak} />
        </div>
      )}

      {/* Sprint 8.2: рекомендация следующей темы (adaptive curriculum) */}
      {nextTopic && (
        <div className="mt-4">
          <NextTopicCard
            next={nextTopic}
            onRefresh={() => {
              api.recommendNext().then(setNextTopic).catch(() => {});
            }}
          />
        </div>
      )}

      <button
        onClick={evaluate}
        disabled={busy}
        className="mt-3 rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50"
      >
        {busy ? "Проверяю..." : "Проверить новые"}
      </button>

      {newlyAwarded.length > 0 && (
        <div className="mt-3 rounded-md bg-emerald-50 p-3 text-sm text-emerald-900">
          🎉 Получены новые баджи: <strong>{newlyAwarded.join(", ")}</strong>
        </div>
      )}

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Полученные ({earned.length})</h2>
        {earned.length === 0 && (
          <p className="mt-2 text-sm text-slate-500">
            Пока нет ни одного баджа. Реши несколько задач — и они появятся.
          </p>
        )}
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {earned.map((b) => (
            <div
              key={b.slug}
              className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-center"
            >
              <div className="text-3xl">{b.icon}</div>
              <div className="mt-1 text-sm font-semibold">{b.title}</div>
              <div className="mt-1 text-xs text-slate-600">{b.description}</div>
              <div className="mt-1 text-[10px] text-emerald-700">
                {new Date(b.awarded_at!).toLocaleDateString("ru")}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Не получены ({locked.length})</h2>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {locked.map((b) => (
            <div
              key={b.slug}
              className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center opacity-60"
            >
              <div className="text-3xl grayscale">🔒</div>
              <div className="mt-1 text-sm font-semibold">{b.title}</div>
              <div className="mt-1 text-xs text-slate-600">{b.description}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
