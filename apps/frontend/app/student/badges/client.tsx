"use client";

// Sprint 3.10 — редизайн /student/badges под prism-shell (как у /parents,
// /admin/ai-providers, /subjects). Список бейджей 4 категориями:
//   - Количество (count): 1, 5, 10, 50, 100, 200, ..., 1500 (всего 15)
//   - Усилие (effort): explained, quality_correct thresholds (5/20/50),
//             mastered, review_count, correct_count thresholds (25/75/150/500)
//             (всего 15)
//   - Серии (streak): streak_3/7/14/30/45/60/100/180/365, streak_correct,
//             returned_after_pause, returned_twice/five (всего 15)
//   - Контекст (context): polymath_week, early_bird, night_owl, weekend_*,
//             perfect_five, ten/twenty/fifty_in_a_row, morning_streak,
//             lunch_*, late_night_hero (всего 15)
//
// Sprint 3.11: расширенный каталог (44 бейджа) + BadgeToast.
// Sprint 3.12: расширен до 60 бейджей (15 в каждой категории).
//
// Полученные — prism-card с gradient-glow, иконка + title + дата.
// Не получены — prism-card с opacity, 🔒.

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import StreakCard from "@/components/StreakCard";
import NextTopicCard from "@/components/NextTopicCard";
import Skeleton from "@/components/Skeleton";
import ErrorState from "@/components/ErrorState";
import BadgeToast, { type BadgeToastItem } from "@/components/BadgeToast";

type BadgeOut = {
  slug: string;
  title: string;
  description: string;
  icon: string;
  awarded_at: string | null;
  evidence: Record<string, unknown>;
};

type Streak = {
  current_streak_days: number;
  longest_streak_days: number;
  total_active_days: number;
  last_active_date: string | null;
  encouragement: string;
};

type NextTopic = {
  topic_id: number | null;
  topic_name: string | null;
  subject_id: number | null;
  subject_name: string | null;
  reason: "weak_topic" | "next_in_curriculum" | "all_mastered";
  mastery_score: number | null;
  encouragement: string;
};

// Категории бейджей (Sprint 3.10: для визуальной группировки).
// Sprint 3.11: расширено до 44 бейджей.
const BADGE_CATEGORIES: Record<string, string> = {
  // Количество решенных задач (count).
  first_step: "count",
  five_solved: "count",
  ten_solved: "count",
  fifty_solved: "count",
  hundred_solved: "count",
  two_hundred_solved: "count",
  three_hundred_solved: "count",
  four_hundred_solved: "count",
  five_hundred_solved: "count",
  six_hundred_solved: "count",
  seven_hundred_solved: "count",
  eight_hundred_solved: "count",
  nine_hundred_solved: "count",
  thousand_solved: "count",
  fifteen_hundred_solved: "count",
  // Усилие / качество (effort).
  explained_in_own_words: "effort",
  five_quality_correct: "effort",
  twenty_quality_correct: "effort",
  fifty_quality_correct: "effort",
  returned_to_hard: "effort",
  mastered_topic: "effort",
  mastered_five_topics: "effort",
  all_basics: "effort",
  review_count_10: "effort",
  review_count_50: "effort",
  asked_question: "effort",
  correct_count_25: "effort",
  correct_count_75: "effort",
  correct_count_150: "effort",
  correct_count_500: "effort",
  // Серии / возвращение (streak).
  streak_3: "streak",
  streak_7: "streak",
  streak_14: "streak",
  streak_30: "streak",
  streak_45: "streak",
  streak_60: "streak",
  streak_100: "streak",
  streak_180: "streak",
  streak_365: "streak",
  returned_after_pause: "streak",
  streak_correct_5: "streak",
  streak_correct_14: "streak",
  streak_correct_30: "streak",
  returned_twice: "streak",
  returned_five: "streak",
  // Контекст (время, разнообразие, серии-правильности).
  polymath_week: "context",
  early_bird: "context",
  night_owl: "context",
  weekend_warrior: "context",
  perfect_five: "context",
  ten_in_a_row: "context",
  twenty_in_a_row: "context",
  fifty_in_a_row: "context",
  morning_streak_5: "context",
  lunch_learner: "context",
  lunch_master: "context",
  late_night_hero: "context",
  weekend_regular_2: "context",
  weekend_master_8: "context",
  morning_streak_14: "context",
};

const CATEGORY_META: Record<string, { label: string; icon: string }> = {
  count: { label: "Количество решённых", icon: "🎯" },
  effort: { label: "Усилие и качество", icon: "✨" },
  streak: { label: "Серии и возвращение", icon: "🔥" },
  context: { label: "Контекст и время", icon: "🌅" },
};

export default function StudentBadgesClient() {
  const [badges, setBadges] = useState<BadgeOut[] | null>(null);
  const [badgesError, setBadgesError] = useState<string | null>(null);
  const [streak, setStreak] = useState<Streak | null>(null);
  const [nextTopic, setNextTopic] = useState<NextTopic | null>(null);
  const [busy, setBusy] = useState(false);
  // Sprint 3.11: теперь хранит {slug, title, icon} для toast.
  const [newlyAwarded, setNewlyAwarded] = useState<BadgeToastItem[]>([]);

  async function refresh() {
    setBusy(true);
    setBadgesError(null);
    try {
      const b = await api.studentBadges();
      setBadges(b);
    } catch (err) {
      setBadgesError(
        err instanceof ApiError
          ? `HTTP ${err.status}: ${err.message}`
          : String(err)
      );
    } finally {
      setBusy(false);
    }
  }

  async function evaluate() {
    setBusy(true);
    try {
      const awarded: string[] = await api.studentBadgesEvaluate();
      // Достаём title + icon для каждого нового бейджа из каталога.
      const summary = await api.studentBadgesCount().catch(() => null);
      const titles = summary?.slug_titles ?? {};
      const icons = summary?.slug_icons ?? {};
      const items: BadgeToastItem[] = awarded.map((slug) => ({
        slug,
        title: titles[slug] ?? slug,
        icon: icons[slug] ?? "🏅",
      }));
      setNewlyAwarded(items);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refresh();
    void api.studentStreak().then(setStreak).catch(() => {});
    void api.recommendNext(3).then(setNextTopic).catch(() => {});
  }, []);

  if (badges === null) {
    if (badgesError) {
      return (
        <ErrorState
          variant="generic"
          error={badgesError}
          onRetry={() => void refresh()}
        />
      );
    }
    // Sprint 3.10: skeleton в prism-стиле (без светлых классов).
    return (
      <div data-testid="badges-skeleton" className="space-y-4">
        <Skeleton width="w-64" height="h-8" />
        <Skeleton width="w-96" height="h-4" />
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mt-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/40 p-4"
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

  // Sprint 3.10: группировка по категориям.
  const earned = badges.filter((b) => b.awarded_at);
  const locked = badges.filter((b) => !b.awarded_at);

  const grouped = (items: BadgeOut[]) => {
    const byCat: Record<string, BadgeOut[]> = { count: [], effort: [], streak: [], context: [] };
    for (const b of items) {
      const cat = BADGE_CATEGORIES[b.slug] ?? "context";
      byCat[cat].push(b);
    }
    return byCat;
  };

  const earnedByCat = grouped(earned);
  const lockedByCat = grouped(locked);

  function renderBadgeCard(b: BadgeOut, isEarned: boolean) {
    return (
      <div
        key={b.slug}
        className={
          "rounded-2xl border p-4 text-center transition-transform " +
          (isEarned
            ? "border-[color:var(--prism-accent)]/40 bg-[color:var(--prism-panel-solid)]/60 shadow-[0_8px_24px_-12px_color-mix(in_srgb,var(--prism-accent)_50%,transparent)] hover:-translate-y-0.5"
            : "border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/25 opacity-55")
        }
      >
        <div className={"text-4xl " + (isEarned ? "" : "grayscale")}>
          {isEarned ? b.icon : "🔒"}
        </div>
        <div className="mt-2 text-sm font-black tracking-tight text-[color:var(--prism-ink)]">
          {b.title}
        </div>
        <div className="mt-1 text-xs leading-snug text-[color:var(--prism-muted)] min-h-[2.5em]">
          {b.description}
        </div>
        {isEarned && b.awarded_at && (
          <div className="mt-2 inline-flex items-center gap-1 rounded-full border border-[color:var(--prism-accent)]/40 bg-[color:var(--prism-accent)]/12 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[color:var(--prism-accent)]">
            ✓ {new Date(b.awarded_at).toLocaleDateString("ru-RU")}
          </div>
        )}
      </div>
    );
  }

  function renderCategorySection(
    catKey: string,
    title: string,
    icon: string,
    earnedItems: BadgeOut[],
    lockedItems: BadgeOut[]
  ) {
    const total = earnedItems.length + lockedItems.length;
    if (total === 0) return null;
    const pct = Math.round((earnedItems.length / total) * 100);
    return (
      <section className="mt-8 first:mt-0">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl" aria-hidden="true">{icon}</span>
          <h2 className="text-lg font-black tracking-[-0.02em] text-[color:var(--prism-ink)]">
            {title}
          </h2>
          <span className="text-xs font-bold text-[color:var(--prism-muted)] ml-auto">
            {earnedItems.length} / {total} · {pct}%
          </span>
        </div>
        <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
          {earnedItems.map((b) => renderBadgeCard(b, true))}
          {lockedItems.map((b) => renderBadgeCard(b, false))}
        </div>
      </section>
    );
  }

  return (
    <div>
      {/* Sprint 3.10: кнопка «Проверить новые» в prism-стиле. */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => void evaluate()}
          disabled={busy}
          className="prism-action primary disabled:opacity-50"
        >
          {busy ? "Проверяю..." : "Проверить новые достижения"}
        </button>
        <button
          onClick={() => void refresh()}
          disabled={busy}
          className="prism-action disabled:opacity-50"
        >
          Обновить
        </button>
      </div>

      {newlyAwarded.length > 0 && (
        <div className="mt-4 rounded-2xl border border-emerald-400/40 bg-emerald-500/10 p-3 text-sm text-emerald-200">
          🎉 Получены новые достижения:{" "}
          <strong>{newlyAwarded.map((b) => b.title).join(", ")}</strong>
        </div>
      )}

      {/* Sprint 3.11: toast с превью новых бейджей (в правом нижнем углу). */}
      <BadgeToast
        badges={newlyAwarded}
        onDismiss={() => setNewlyAwarded([])}
      />

      {/* Streak + Next topic — без изменений (Sprint 8.1, 8.2). */}
      {streak && (
        <div className="mt-6">
          <StreakCard streak={streak} />
        </div>
      )}
      {nextTopic && (
        <div className="mt-6">
          <NextTopicCard
            next={nextTopic}
            onRefresh={() => {
              void api.recommendNext(3).then(setNextTopic).catch(() => {});
            }}
          />
        </div>
      )}

      {/* Sprint 3.10: статистика по badge. */}
      <div className="mt-8 grid gap-3 grid-cols-2 sm:grid-cols-3">
        <div className="rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-4">
          <div className="text-xs font-black uppercase tracking-[0.16em] text-[color:var(--prism-muted)]">
            Получено
          </div>
          <div className="mt-1 text-3xl font-black text-[color:var(--prism-accent)]">
            {earned.length}
          </div>
          <div className="text-xs text-[color:var(--prism-muted)]">из {badges.length}</div>
        </div>
        <div className="rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-4">
          <div className="text-xs font-black uppercase tracking-[0.16em] text-[color:var(--prism-muted)]">
            Прогресс
          </div>
          <div className="mt-1 text-3xl font-black text-[color:var(--prism-green)]">
            {badges.length > 0
              ? `${Math.round((earned.length / badges.length) * 100)}%`
              : "—"}
          </div>
          <div className="text-xs text-[color:var(--prism-muted)]">всего достижений</div>
        </div>
        <div className="rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-4">
          <div className="text-xs font-black uppercase tracking-[0.16em] text-[color:var(--prism-muted)]">
            Категорий
          </div>
          <div className="mt-1 text-3xl font-black text-[color:var(--prism-ink)]">
            {Object.keys(CATEGORY_META).filter(
              (k) => (earnedByCat[k]?.length ?? 0) > 0
            ).length}{" "}
            <span className="text-base text-[color:var(--prism-muted)]">из 4</span>
          </div>
          <div className="text-xs text-[color:var(--prism-muted)]">активных</div>
        </div>
      </div>

      {/* Категории бейджей. */}
      {(["count", "effort", "streak", "context"] as const).map((k) =>
        renderCategorySection(
          k,
          CATEGORY_META[k].label,
          CATEGORY_META[k].icon,
          earnedByCat[k],
          lockedByCat[k]
        )
      )}

      {earned.length === 0 && (
        <div className="mt-8 rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/35 p-6 text-center">
          <div className="text-3xl">🎯</div>
          <div className="mt-2 text-sm text-[color:var(--prism-muted)]">
            Пока нет достижений. Реши несколько задач — и они появятся.
          </div>
        </div>
      )}
    </div>
  );
}
