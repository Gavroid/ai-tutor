"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import Header from "@/components/Header";
import type { User } from "@/types";

type SubjectMastery = {
  subject_id: number;
  subject_name: string;
  topics_total: number;
  topics_attempted: number;
  avg_mastery: number;
  accuracy: number;
};

type WeakTopic = {
  topic_id: number;
  topic_name: string;
  subject_name: string;
  mastery: number;
  attempts_count: number;
};

type TopMistake = {
  mistake_type: string;
  description: string;
  topic_id: number;
  topic_name: string;
  count: number;
  last_seen: string;
};

type StudyStreak = {
  current_streak_days: number;
  longest_streak_days: number;
  last_active_date: string | null;
  total_active_days: number;
};

type TimeStats = {
  total_attempts: number;
  last_7_days: number;
  last_30_days: number;
  avg_per_active_day: number;
};

type ParentRecommendation = {
  title: string;
  detail: string;
  tone: "neutral" | "info" | "warning" | "success" | string;
  topic_id: number | null;
  topic_name: string | null;
};

type Dashboard = {
  student: { id: number; display_name: string; email: string };
  generated_at: string;
  total_attempts: number;
  correct_attempts: number;
  accuracy: number;
  average_mastery: number;
  subject_mastery: SubjectMastery[];
  weak_topics: WeakTopic[];
  top_mistakes: TopMistake[];
  streak: StudyStreak;
  time_stats: TimeStats;
  daily_activity_30d: Array<{ date: string; attempts: number }>;
  due_for_review_count: number;
  summary: string;
  recommendations: ParentRecommendation[];
  last_activity_label: string;
  privacy_note: string;
};

export default function ParentDashboardPage() {
  const router = useRouter();
  const params = useParams<{ studentId: string }>();
  const studentId = Number(params.studentId);
  const [user, setUser] = useState<User | null>(null);
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [displaySettings, setDisplaySettings] = useState({
    showMistakes: true,
    showWeakTopics: true,
    showActivity: true,
  });
  // Sprint 3.11: бейджи ребёнка для отображения на дашборде.
  const [badges, setBadges] = useState<Awaited<
    ReturnType<typeof api.parentChildBadges>
  > | null>(null);

  useEffect(() => {
    api.me().then(setUser).catch(() => router.push("/login"));
    if (!studentId || Number.isNaN(studentId)) return;
    refresh();
    refreshBadges();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId]);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      const data = await api.parentDashboard(studentId);
      setDash(data as Dashboard);
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 401) {
        router.push("/login");
        return;
      }
      setError(e instanceof Error ? e.message : "Ошибка загрузки дашборда");
    } finally {
      setBusy(false);
    }
  }

  async function refreshBadges() {
    try {
      const data = await api.parentChildBadges(studentId);
      setBadges(data);
      // Sprint 3.13: если родитель открыл дашборд впервые — отмечаем
      // все бейджи как просмотренные (чтобы при следующем заходе
      // корректно показать "X новых").
      if (data.new_since_last_seen === null) {
        api.parentChildBadgesSeen(studentId).catch(() => {});
      }
    } catch (e) {
      // Тихо — бейджи это дополнительная фича, не критично.
      if (e instanceof ApiError && e.status === 401) return;
    }
  }

  async function dismissNewBadgesBanner() {
    if (!badges || badges.new_since_last_seen === null) return;
    try {
      const r = await api.parentChildBadgesSeen(studentId);
      // Обновим локальный state.
      setBadges((prev) => (prev ? { ...prev, new_since_last_seen: 0, new_items: [] } : prev));
    } catch {
      // ignore
    }
  }

  if (!dash) {
    return (
      <main className="prism-shell parent-dashboard-console min-h-dvh">
        <Header user={user} backHref="/parents" title="Родительский дашборд" />
        <section className="grid min-h-[calc(100dvh-80px)] place-items-center p-4">
        <div className="prism-card pad w-full max-w-xl text-center">
          <div className="prism-kicker mx-auto w-fit">Parent Monitor</div>
          <h1 className="mt-4 text-4xl font-black tracking-[-0.05em]">Родительский дашборд</h1>
          {error && <div className="mt-5 rounded-3xl border border-red-400/30 bg-red-500/10 p-4 text-sm font-bold text-red-500">{error}</div>}
          <p className="mt-5 text-[color:var(--prism-muted)]">{busy ? "Загрузка дашборда…" : "Нет данных"}</p>
          <Link href="/parents" className="prism-action mt-6">← К списку детей</Link>
        </div>
        </section>
      </main>
    );
  }

  const generatedAt = new Date(dash.generated_at).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const weeklyAttempts = dash.daily_activity_30d.slice(-7).reduce((sum, day) => sum + day.attempts, 0);
  const weeklyActiveDays = dash.daily_activity_30d.slice(-7).filter((day) => day.attempts > 0).length;
  const weeklySummary = (() => {
    if (weeklyAttempts === 0) return "За неделю занятий не было — лучше начать с 10 минут лёгкой практики.";
    if (dash.accuracy < 0.6) return "Неделя была активной, но точность просела — сначала повторить правило, потом решать новые задачи.";
    if (dash.weak_topics.length > 0) return `Главный фокус недели: «${dash.weak_topics[0].topic_name}». Достаточно 2–3 коротких задач.`;
    return "Неделя выглядит ровно: можно продолжать текущий темп и брать одну задачу на закрепление.";
  })();
  const tomorrowPlan = (() => {
    if (dash.weak_topics.length > 0) return `Завтра: 10 минут на «${dash.weak_topics[0].topic_name}» — сначала объяснение, потом одна практика.`;
    if (dash.due_for_review_count > 0) return `Завтра: повторить ${dash.due_for_review_count} тем(ы), которые пора закрепить.`;
    if (weeklyAttempts === 0) return "Завтра: выбрать одну короткую тему и решить 2–3 простые задачи.";
    return "Завтра: сохранить темп — одно объяснение и одна задача на закрепление.";
  })();
  const primarySubject = dash.subject_mastery[0] ?? null;
  const routeProgress = primarySubject
    ? `${primarySubject.topics_attempted}/${primarySubject.topics_total} тем · mastery ${Math.round(primarySubject.avg_mastery * 100)}%`
    : "Маршрут пока не начат";
  const improvementSignal = (() => {
    if (weeklyAttempts === 0) return "На этой неделе ещё нет учебной активности.";
    if (dash.accuracy >= 0.8) return "Ребёнок уверенно отвечает: можно закреплять и двигаться по маршруту.";
    if (dash.accuracy >= 0.6) return "Есть рабочий темп: важно сохранить регулярность и короткие повторения.";
    return "Активность есть, но точность просела: сейчас важнее повторение, чем новые темы.";
  })();
  const helpSignal = dash.weak_topics[0]
    ? `Помочь с темой «${dash.weak_topics[0].topic_name}»: сначала правило, затем 2–3 простые задачи.`
    : dash.due_for_review_count > 0
      ? `Помочь с повторением: к закреплению ${dash.due_for_review_count} тем(ы).`
      : "Явных слабых тем нет — достаточно короткого контроля и поддержки регулярности.";
  const exportHref = `/api/v1/parents/students/${studentId}/dashboard.pdf`;

  return (
    <main className="prism-shell parent-dashboard-console min-h-dvh">
      <Header user={user} backHref="/parents" title="Родительский дашборд" />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer p-5 lg:p-10">
          <Link href="/parents" className="prism-pill">← К списку детей</Link>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1.05fr_0.95fr] xl:items-end">
            <div>
              <div className="prism-kicker">Monitor · Parent View</div>
              <h1 className="prism-title">Прогресс <span className="accent">{dash.student.display_name}</span></h1>
              <p className="prism-copy">Не сухая статистика, а карта: что происходит сейчас, что повторить и где нужна поддержка взрослого.</p>
              <p className="mt-4 text-sm text-[color:var(--prism-muted)]">Обновлено: {generatedAt}</p>
            </div>

            <aside className="prism-card pad glow">
              <div className="text-xs font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">Что важно сейчас</div>
              <p className="mt-3 text-xl font-black leading-snug">{dash.summary}</p>
              <p className="mt-3 text-sm text-[color:var(--prism-muted)]">Последняя активность: {dash.last_activity_label}</p>
              <div className="mt-4 rounded-3xl border border-[color:var(--prism-line)] bg-black/10 p-4">
                <div className="prism-kicker">Weekly Summary</div>
                <p className="mt-2 text-sm leading-6 text-[color:var(--prism-ink)]">{weeklySummary}</p>
                <div className="mt-3 rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/40 p-3 text-sm font-black text-[color:var(--prism-ink)]">
                  Что сделать завтра: {tomorrowPlan}
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <Metric label="7 дней" value={weeklyAttempts} />
                  <Metric label="Активных дней" value={weeklyActiveDays} />
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <a href={exportHref} target="_blank" rel="noreferrer" className="prism-action px-4 py-2 text-sm">Экспорт HTML/PDF</a>
                <button type="button" onClick={refresh} disabled={busy} className="prism-action px-4 py-2 text-sm disabled:opacity-50">Обновить</button>
              </div>
            </aside>
          </div>

          <section className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label="Попыток всего" value={dash.total_attempts} />
            <Metric label="Точность" value={`${Math.round(dash.accuracy * 100)}%`} hot={dash.accuracy >= 0.7} />
            <Metric label="Средний mastery" value={`${Math.round(dash.average_mastery * 100)}%`} />
            <Metric label="К повторению" value={dash.due_for_review_count} hot={dash.due_for_review_count === 0} />
          </section>

          <section className="mt-4 grid gap-3 lg:grid-cols-4" aria-label="Краткий родительский отчёт">
            <ParentInsight title="Что улучшилось" body={improvementSignal} tone={dash.accuracy >= 0.75 ? "success" : "info"} />
            <ParentInsight title="Где нужна помощь" body={helpSignal} tone={dash.weak_topics.length > 0 || dash.accuracy < 0.6 ? "warning" : "success"} />
            <ParentInsight title="Что сделать завтра" body={tomorrowPlan} tone="info" />
            <ParentInsight title="Маршрут" body={routeProgress} tone="neutral" />
          </section>

          {/* Sprint 3.13: баннер «🎉 +X новых с прошлого визита». */}
          {badges && badges.new_since_last_seen !== null && badges.new_since_last_seen > 0 && (
            <section className="mt-4" aria-label="Новые достижения ребёнка" data-testid="parent-badges-new-banner">
              <div className="prism-card pad border border-emerald-400/50 bg-gradient-to-br from-emerald-500/15 via-[color:var(--prism-panel-solid)] to-[color:var(--prism-panel-solid)] shadow-[0_18px_50px_-15px_rgba(16,185,129,0.35)]">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <span aria-hidden className="text-3xl leading-none">🎉</span>
                    <div>
                      <div className="text-[11px] font-black uppercase tracking-[0.16em] text-emerald-300">
                        С прошлого визита
                      </div>
                      <div className="mt-1 text-lg font-black tracking-[-0.02em] text-[color:var(--prism-ink)]">
                        +{badges.new_since_last_seen}{" "}
                        {badges.new_since_last_seen === 1 ? "новое достижение" : "новых достижений"}
                      </div>
                      {badges.new_items.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {badges.new_items.slice(0, 5).map((b) => (
                            <span
                              key={b.slug}
                              className="inline-flex items-center gap-1 rounded-full border border-emerald-400/40 bg-emerald-500/10 px-2 py-0.5 text-xs"
                              title={b.title}
                            >
                              <span aria-hidden>{b.icon}</span>
                              {b.title}
                            </span>
                          ))}
                          {badges.new_items.length > 5 && (
                            <span className="inline-flex items-center rounded-full border border-emerald-400/40 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-200">
                              +{badges.new_items.length - 5} ещё
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => void dismissNewBadgesBanner()}
                    className="prism-action px-4 py-2 text-sm"
                  >
                    Понятно
                  </button>
                </div>
              </div>
            </section>
          )}

          {/* Sprint 3.11: бейджи ребёнка (только чтение, без влияния). */}
          {badges && (
            <section className="mt-4" aria-label="Достижения ребёнка">
              <div className="prism-card pad" data-testid="parent-badges-card">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="prism-kicker">Достижения</div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-3xl font-black tabular-nums text-[color:var(--prism-accent)]">
                        {badges.total_earned}
                      </span>
                      <span className="text-sm text-[color:var(--prism-muted)]">
                        из {badges.total_available}
                      </span>
                    </div>
                  </div>
                  {badges.latest && (
                    <div className="hidden sm:flex items-center gap-2 rounded-2xl border border-emerald-400/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
                      <span aria-hidden className="text-xl">{badges.latest.icon}</span>
                      <div className="min-w-0">
                        <div className="text-[10px] font-black uppercase tracking-[0.16em] text-emerald-300/80">
                          Последний
                        </div>
                        <div className="truncate font-black">{badges.latest.title}</div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Прогресс по категориям. */}
                <div className="mt-4 grid gap-2 grid-cols-2 sm:grid-cols-4">
                  {(["count", "effort", "streak", "context"] as const).map((cat) => {
                    const value = badges.by_category[cat] ?? "0 / 0";
                    const labels: Record<string, string> = {
                      count: "Количество",
                      effort: "Усилие",
                      streak: "Серии",
                      context: "Контекст",
                    };
                    const icons: Record<string, string> = {
                      count: "🎯",
                      effort: "✨",
                      streak: "🔥",
                      context: "🌅",
                    };
                    return (
                      <div
                        key={cat}
                        className="rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-3"
                        data-testid={`parent-badges-cat-${cat}`}
                      >
                        <div className="flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.14em] text-[color:var(--prism-muted)]">
                          <span aria-hidden>{icons[cat]}</span>
                          {labels[cat]}
                        </div>
                        <div className="mt-1 text-lg font-black tabular-nums text-[color:var(--prism-ink)]">
                          {value}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Превью последних 5 earned. */}
                {badges.earned.length > 0 && (
                  <div className="mt-4">
                    <div className="text-[11px] font-black uppercase tracking-[0.14em] text-[color:var(--prism-muted)]">
                      Недавние достижения
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {badges.earned.slice(0, 5).map((b) => (
                        <div
                          key={b.slug}
                          title={`${b.title} — ${new Date(b.earned_at).toLocaleDateString("ru-RU")}`}
                          className="flex items-center gap-1.5 rounded-full border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 px-3 py-1.5 text-sm"
                        >
                          <span aria-hidden>{b.icon}</span>
                          <span className="font-black">{b.title}</span>
                        </div>
                      ))}
                      {badges.earned.length > 5 && (
                        <div className="rounded-full border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 px-3 py-1.5 text-sm text-[color:var(--prism-muted)]">
                          +{badges.earned.length - 5} ещё
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <p className="mt-3 text-xs text-[color:var(--prism-muted)]">
                  Родитель видит только список достижений. Содержание чатов ребёнка
                  с репетитором остаётся приватным.
                </p>
              </div>
            </section>
          )}

          <section className="mt-4 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
            <div className="prism-card pad">
              <div className="prism-kicker">Recommendations</div>
              <div className="mt-4 grid gap-3">
                {dash.recommendations.map((rec, idx) => <RecommendationCard key={`${rec.title}-${idx}`} rec={rec} />)}
              </div>
            </div>

            {displaySettings.showActivity && <div className="prism-card pad">
              <div className="prism-kicker">30 Day Pulse</div>
              <div className="mt-5 flex h-36 items-end gap-1.5">
                {dash.daily_activity_30d.map((d) => {
                  const max = Math.max(...dash.daily_activity_30d.map((x) => x.attempts), 1);
                  const h = Math.max(3, Math.round((d.attempts / max) * 100));
                  return <div key={d.date} title={`${d.date}: ${d.attempts} попыток`} className={`flex-1 rounded-t-lg ${d.attempts > 0 ? "bg-[color:var(--prism-accent)]" : "bg-[color:var(--prism-line)]"}`} style={{ height: `${h}%` }} />;
                })}
              </div>
              <div className="mt-2 flex justify-between text-[10px] text-[color:var(--prism-muted)]"><span>{dash.daily_activity_30d[0]?.date.slice(5)}</span><span>сегодня: {dash.daily_activity_30d.at(-1)?.date.slice(5)}</span></div>
            </div>}
          </section>

          <section className="parent-dashboard-grid mt-6">
            <div className="parent-dashboard-stack">
              <div className="prism-card pad parent-streak-card">
                <div className="prism-kicker">Streak</div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <Metric label="Сегодняшняя серия" value={`${dash.streak.current_streak_days}д`} />
                  <Metric label="Лучшая серия" value={`${dash.streak.longest_streak_days}д`} />
                  <Metric label="Активных дней" value={dash.streak.total_active_days} />
                  <Metric label="7 дней" value={`${dash.time_stats.last_7_days} попыток`} />
                </div>
                <div className="mt-4 rounded-3xl border border-[color:var(--prism-line)] bg-black/10 p-4 text-sm text-[color:var(--prism-muted)]">
                  <div className="font-black text-[color:var(--prism-ink)]">Последний активный день: {dash.streak.last_active_date ?? "пока нет"}</div>
                  <div className="mt-1">Средний темп: {dash.time_stats.avg_per_active_day} попыток за активный день · 30 дней: {dash.time_stats.last_30_days} попыток.</div>
                </div>
              </div>

              {displaySettings.showWeakTopics && dash.weak_topics.length > 0 && (
                <div className="prism-card pad">
                  <div className="prism-kicker">Weak Signals</div>
                  <div className="mt-4 grid gap-2">
                    {/* Sprint 3.16: единый лимит с /subjects (5). */}
                    {dash.weak_topics.slice(0, 5).map((w) => (
                      <Link key={w.topic_id} href={`/topics/${w.topic_id}`} className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-3 hover:border-[color:var(--prism-accent)]">
                        <div className="font-black">{w.subject_name}: {w.topic_name}</div>
                        <div className="mt-1 text-xs text-[color:var(--prism-muted)]">mastery {Math.round(w.mastery * 100)}% · попыток {w.attempts_count}</div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {displaySettings.showMistakes && dash.top_mistakes.length > 0 && (
                <div className="prism-card pad">
                  <div className="prism-kicker">Mistake Pattern</div>
                  <div className="mt-4 grid gap-2">
                    {dash.top_mistakes.slice(0, 5).map((m, i) => (
                      <div key={`${m.topic_id}-${i}`} className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-3">
                        <div className="flex items-center justify-between gap-3"><span className="font-black">{m.topic_name}</span><span className="prism-pill">×{m.count}</span></div>
                        <div className="mt-1 text-xs text-[color:var(--prism-muted)]">{m.mistake_type}: {m.description}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="prism-card pad parent-mastery-card">
              <div className="prism-kicker">Mastery Map</div>
              <div className="mt-4 space-y-4">
                {dash.subject_mastery.length > 0 ? dash.subject_mastery.map((sm) => <SubjectBar key={sm.subject_id} sm={sm} />) : <p className="text-sm text-[color:var(--prism-muted)]">Нет данных</p>}
              </div>
            </div>
          </section>

          <section className="prism-card pad mt-6">
            <div className="prism-kicker">Parent Display Settings</div>
            <p className="mt-2 text-sm text-[color:var(--prism-muted)]">Локальные настройки вида: меняют только этот экран, не раскрывают чат ребёнка.</p>
            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              {[
                ["showWeakTopics", "Слабые темы"],
                ["showMistakes", "Типичные ошибки"],
                ["showActivity", "Активность"],
              ].map(([key, label]) => (
                <label key={key} className="prism-toggle-pill">
                  <input
                    type="checkbox"
                    checked={displaySettings[key as keyof typeof displaySettings]}
                    onChange={(event) => setDisplaySettings((prev) => ({ ...prev, [key]: event.target.checked }))}
                    className="sr-only"
                  />
                  <span aria-hidden="true" className="prism-toggle-dot" />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </section>

          <section className="prism-card pad mt-6 text-sm text-[color:var(--prism-muted)]">
            🔒 {dash.privacy_note}
          </section>
        </div>
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value, hot = false }: { label: string; value: string | number; hot?: boolean }) {
  return <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/50 p-4"><div className="text-[10px] font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">{label}</div><div className={`mt-1 text-2xl font-black ${hot ? "text-[color:var(--prism-green)]" : ""}`}>{value}</div></div>;
}

function RecommendationCard({ rec }: { rec: ParentRecommendation }) {
  return <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-4"><div className="font-black">{rec.title}</div><div className="mt-1 text-sm text-[color:var(--prism-muted)]">{rec.detail}</div>{rec.topic_id && <Link href={`/topics/${rec.topic_id}`} className="prism-pill mt-3">Открыть тему</Link>}</div>;
}

function ParentInsight({ title, body, tone }: { title: string; body: string; tone: "success" | "warning" | "info" | "neutral" }) {
  const toneClass = tone === "success" ? "border-emerald-400/30" : tone === "warning" ? "border-amber-400/35" : tone === "info" ? "border-sky-400/30" : "border-[color:var(--prism-line)]";
  return (
    <article className={`rounded-3xl border ${toneClass} bg-[color:var(--prism-panel-solid)]/45 p-4`}>
      <div className="text-[10px] font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">{title}</div>
      <p className="mt-2 text-sm font-bold leading-6 text-[color:var(--prism-ink)]">{body}</p>
    </article>
  );
}

function SubjectBar({ sm }: { sm: SubjectMastery }) {
  const masteryPct = Math.round(sm.avg_mastery * 100);
  const accuracyPct = Math.round(sm.accuracy * 100);
  const color = masteryPct >= 75 ? "bg-emerald-500" : masteryPct >= 50 ? "bg-amber-500" : "bg-rose-500";
  return <div><div className="flex items-center justify-between gap-3 text-sm"><span className="font-black">{sm.subject_name}</span><span className="text-xs text-[color:var(--prism-muted)]">{sm.topics_attempted}/{sm.topics_total} тем · точность {accuracyPct}%</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-[color:var(--prism-line)]"><div className={`h-full ${color}`} style={{ width: `${masteryPct}%` }} /></div></div>;
}
