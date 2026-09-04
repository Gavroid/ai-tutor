"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import Header from "@/components/Header";
import type { User } from "@/types";

type LinkedStudent = {
  student_id: number;
  display_name: string;
  email: string;
  linked_at: string;
};

// Sprint 3.13: badge counter "N новых с прошлого визита" для каждого ребёнка.
type NewBadgesByChild = Record<number, number>;

type Overview = {
  student: { id: number; display_name: string; email: string };
  total_attempts: number;
  correct_attempts: number;
  accuracy: number;
  average_mastery: number;
  weak_topics: Array<{ topic_id: number; topic_name: string; subject_name: string; mastery: number; attempts_count: number }>;
  daily_activity: Array<{ date: string; attempts: number }>;
  privacy_note: string;
};

function formatActivityDay(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}


function buildParentRecommendations(overview: Overview): string[] {
  const recommendations: string[] = [];
  if (overview.total_attempts === 0) {
    return ["Начните с одного короткого занятия: открыть тему, попросить объяснение и решить 1 задачу."];
  }
  if (overview.accuracy < 0.6) {
    recommendations.push("Сделайте короткое повторение: пусть ребёнок объяснит правило своими словами перед новой задачей.");
  }
  // Sprint 3.17: до 5 тем в рекомендациях (как у ученика в /subjects).
  const weakForRecs = overview.weak_topics.slice(0, 5);
  for (const topic of weakForRecs) {
    recommendations.push(
      `Вернитесь к теме «${topic.topic_name}» (mastery ${Math.round(topic.mastery * 100)}%) и решите 2–3 простые задачи.`
    );
  }
  const recentActive = overview.daily_activity.slice(-7).some((day) => day.attempts > 0);
  if (!recentActive) {
    recommendations.push("Запланируйте мягкий возврат: 10 минут практики сегодня без длинной сессии.");
  }
  if (recommendations.length === 0) {
    recommendations.push("Темп нормальный: продолжайте короткие регулярные занятия и добавьте одну задачу на закрепление.");
  }
  // Sprint 3.17: max=5 рекомендаций (Игорь).
  return recommendations.slice(0, 5);
}

function summarizeActivity(days: Array<{ date: string; attempts: number }>) {
  const activeDays = days.filter((day) => day.attempts > 0);
  const total = activeDays.reduce((sum, day) => sum + day.attempts, 0);
  const peak = activeDays.reduce<{ date: string; attempts: number } | null>(
    (best, day) => (!best || day.attempts > best.attempts ? day : best),
    null,
  );
  const last = activeDays.at(-1) ?? null;
  return {
    activeDays: activeDays.length,
    total,
    average: activeDays.length ? Math.round(total / activeDays.length) : 0,
    peak,
    last,
  };
}

export default function ParentsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [children, setChildren] = useState<LinkedStudent[]>([]);
  const [invite, setInvite] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [overviewByChild, setOverviewByChild] = useState<Record<number, Overview>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyInvite, setBusyInvite] = useState(false);
  const [loadingChildren, setLoadingChildren] = useState(true);
  // Sprint 3.13: количество "новых бейджей с прошлого визита" на каждого ребёнка.
  const [newBadges, setNewBadges] = useState<NewBadgesByChild>({});

  useEffect(() => {
    api.me().then(setUser).catch(() => router.push("/login"));
    refresh();
  }, [router]);

  function refresh() {
    setLoadingChildren(true);
    api
      .parentsChildren()
      .then(async (linkedChildren) => {
        setChildren(linkedChildren);
        if (linkedChildren.length === 0) {
          setSelectedId(null);
          setOverview(null);
          setOverviewByChild({});
          setNewBadges({});
          return;
        }

        const results = await Promise.allSettled(
          linkedChildren.map(async (child) => [child.student_id, await api.parentsOverview(child.student_id)] as const),
        );
        const loaded = Object.fromEntries(
          results
            .filter((result): result is PromiseFulfilledResult<readonly [number, Overview]> => result.status === "fulfilled")
            .map((result) => result.value),
        );
        setOverviewByChild(loaded);

        // Sprint 3.13: подгружаем "новые бейджи" для каждого ребёнка
        // параллельно с overview — чтобы список не мигал дважды.
        const badgeResults = await Promise.allSettled(
          linkedChildren.map(async (child) => {
            const data = await api.parentChildBadges(child.student_id);
            return [child.student_id, data.new_since_last_seen ?? 0] as const;
          }),
        );
        const newBadgesMap: NewBadgesByChild = {};
        badgeResults.forEach((r) => {
          if (r.status === "fulfilled") {
            newBadgesMap[r.value[0]] = r.value[1];
          }
        });
        setNewBadges(newBadgesMap);

        const saved = typeof window !== "undefined" ? Number(localStorage.getItem("ai-tutor:parent:selected")) : 0;
        const savedChild = linkedChildren.find((child) => child.student_id === saved);
        const childWithData = linkedChildren.find((child) => (loaded[child.student_id]?.total_attempts ?? 0) > 0);
        const nextId = childWithData?.student_id ?? savedChild?.student_id ?? linkedChildren[0].student_id;
        setSelectedId(nextId);
        setOverview(loaded[nextId] ?? null);
        try {
          localStorage.setItem("ai-tutor:parent:selected", String(nextId));
        } catch {
          // ignore storage issues
        }
      })
      .catch(() => setError("Не удалось загрузить список детей"))
      .finally(() => setLoadingChildren(false));
  }

  function pickChild(id: number) {
    setSelectedId(id);
    setOverview(overviewByChild[id] ?? null);
    try {
      localStorage.setItem("ai-tutor:parent:selected", String(id));
    } catch {
      // ignore storage issues
    }
  }

  useEffect(() => {
    if (!selectedId || overviewByChild[selectedId]) return;
    api.parentsOverview(selectedId).then(setOverview).catch(() => setOverview(null));
  }, [selectedId, overviewByChild]);

  async function createInvite() {
    setBusyInvite(true);
    setError(null);
    try {
      const response = await api.parentsInvite();
      setInvite(response.code);
    } catch {
      setError("Не удалось создать код");
    } finally {
      setBusyInvite(false);
    }
  }

  return (
    <main className="prism-shell parents-console min-h-dvh">
      <Header user={user} backHref="/subjects" title="Parent Console" />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer p-5 lg:p-10">
          <Link href="/subjects" className="prism-pill">← На главную</Link>

          <div className="mt-7 grid gap-6 xl:grid-cols-[1fr_0.95fr] xl:items-end">
            <section>
              <div className="prism-kicker">Parent Console</div>
              <h1 className="prism-title">Родительский <span className="accent">кабинет</span></h1>
              <p className="prism-copy">Создай код для ребёнка, выбери привязанный профиль и открой расширенный мониторинг прогресса. Переписка с AI остаётся приватной.</p>
            </section>

            <aside className="prism-card pad glow">
              <div className="text-xs font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">Привязать ребёнка</div>
              <p className="mt-3 text-sm leading-6 text-[color:var(--prism-muted)]">Код вводится в кабинете ребёнка. После привязки родитель видит прогресс, слабые темы и рекомендации.</p>
              <button onClick={createInvite} disabled={busyInvite} className="prism-action primary mt-5 w-fit px-6">
                {busyInvite ? "Создаю код…" : "Создать код"}
              </button>
              {invite && (
                <div className="mt-4 rounded-3xl border border-[color:var(--prism-line)] bg-black/10 p-4">
                  <div className="text-xs font-black uppercase tracking-[0.16em] text-[color:var(--prism-muted)]">Код для ребёнка</div>
                  <div className="mt-2 break-all font-mono text-2xl font-black tracking-[0.14em] text-[color:var(--prism-ink)]">{invite}</div>
                  <p className="mt-2 text-xs text-[color:var(--prism-muted)]">Попроси ребёнка открыть “Привязать родителя” и ввести этот код.</p>
                </div>
              )}
            </aside>
          </div>

          {error && <div className="mt-5 rounded-3xl border border-rose-300/30 bg-rose-400/10 p-4 text-sm font-bold text-rose-200">{error}</div>}

          <section className="mt-6 grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
            <aside className="prism-card pad">
              <div className="prism-kicker">Дети</div>
              {loadingChildren ? (
                <p className="mt-4 text-sm text-[color:var(--prism-muted)]">Загружаю список…</p>
              ) : children.length === 0 ? (
                <div className="mt-4 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/40 p-4">
                  <div className="text-xl font-black text-[color:var(--prism-ink)]">Пока никого нет</div>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--prism-muted)]">Создай код выше и попроси ребёнка ввести его в разделе “Привязать родителя”.</p>
                </div>
              ) : (
                <div className="mt-4 grid gap-2">
                  {children.map((child) => {
                    const newCount = newBadges[child.student_id] ?? 0;
                    return (
                    <div key={child.student_id} className={`rounded-3xl border p-3 ${selectedId === child.student_id ? "border-[color:var(--prism-accent)] bg-[color:var(--prism-panel-solid)]/55 shadow-glow" : "border-[color:var(--prism-line)] bg-black/10"}`}>
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <button onClick={() => pickChild(child.student_id)} className="min-w-0 flex-1 text-left">
                          <div className="flex items-center gap-2">
                            <span className="font-black text-[color:var(--prism-ink)]">{child.display_name}</span>
                            {/* Sprint 3.13: pill «N новых» рядом с именем. */}
                            {newCount > 0 && (
                              <span
                                className="inline-flex items-center gap-1 rounded-full border border-emerald-400/50 bg-emerald-500/15 px-2 py-0.5 text-[11px] font-black text-emerald-200"
                                title={`${newCount} ${newCount === 1 ? "новое достижение" : "новых достижений"} с прошлого визита`}
                                data-testid={`parent-child-new-badges-${child.student_id}`}
                              >
                                <span aria-hidden>🏅</span>
                                +{newCount}
                              </span>
                            )}
                          </div>
                          <div className="mt-1 text-xs text-[color:var(--prism-muted)]">
                            Привязан: {new Date(child.linked_at).toLocaleDateString("ru-RU")}
                            {overviewByChild[child.student_id] && ` · попыток ${overviewByChild[child.student_id].total_attempts}`}
                          </div>
                        </button>
                        <Link href={`/parent/dashboard/${child.student_id}`} className="prism-action shrink-0 px-4 py-2 text-sm">Дашборд</Link>
                      </div>
                    </div>
                    );
                  })}
                </div>
              )}
            </aside>

            <section className="grid gap-4">
              <div className="prism-card pad">
                <div className="prism-kicker">Сводка</div>
                {overview ? (
                  <>
                    <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
                      <Stat label="Заданий" value={overview.total_attempts} />
                      <Stat label="Верно" value={overview.correct_attempts} />
                      <Stat label="Точность" value={`${Math.round(overview.accuracy * 100)}%`} />
                      <Stat label="Mastery" value={`${Math.round(overview.average_mastery * 100)}%`} />
                    </div>
                    <div className="mt-4 rounded-3xl border border-[color:var(--prism-line)] bg-black/10 p-4 text-sm text-[color:var(--prism-muted)]">🔒 {overview.privacy_note}</div>
                    <div className="mt-4 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-4">
                      <div className="prism-kicker">Что делать дальше</div>
                      <ul className="mt-3 grid gap-2 text-sm leading-6 text-[color:var(--prism-ink)]">
                        {buildParentRecommendations(overview).map((item) => <li key={item}>• {item}</li>)}
                      </ul>
                    </div>
                  </>
                ) : (
                  <p className="mt-4 text-sm text-[color:var(--prism-muted)]">Выбери ребёнка слева, чтобы увидеть краткую сводку.</p>
                )}
              </div>

              {overview && (
                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="prism-card pad">
                    <div className="prism-kicker">Слабые темы</div>
                    {overview.weak_topics.length === 0 ? (
                      <p className="mt-4 text-sm text-[color:var(--prism-muted)]">Нет слабых тем — хороший знак.</p>
                    ) : (
                      <div className="mt-4 grid gap-2">
                        {overview.weak_topics.slice(0, 5).map((topic) => (
                          <Link key={topic.topic_id} href={`/topics/${topic.topic_id}`} className="prism-review-row block rounded-2xl border border-[color:var(--prism-line)] px-3 py-2">
                            <div className="font-black text-[color:var(--prism-ink)]">{topic.topic_name}</div>
                            <div className="mt-1 text-xs text-[color:var(--prism-muted)]">{topic.subject_name} · mastery {Math.round(topic.mastery * 100)}% · попыток {topic.attempts_count}</div>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="prism-card pad parent-activity-card">
                    <div className="prism-kicker">Активность</div>
                    {overview.daily_activity.length === 0 ? (
                      <p className="mt-4 text-sm text-[color:var(--prism-muted)]">Первые занятия ещё не появились.</p>
                    ) : (() => {
                      const summary = summarizeActivity(overview.daily_activity);
                      const max = Math.max(...overview.daily_activity.map((item) => item.attempts), 1);
                      const recentDays = overview.daily_activity.slice(-14);
                      return (
                        <div className="mt-4 space-y-4">
                          <div className="grid grid-cols-2 gap-2">
                            <ActivityStat label="За период" value={summary.total} note="попыток" />
                            <ActivityStat label="Активных дней" value={summary.activeDays} note="с занятиями" />
                            <ActivityStat label="Средний темп" value={summary.average} note="попыток / день" />
                            <ActivityStat label="Пик" value={summary.peak ? summary.peak.attempts : 0} note={summary.peak ? formatActivityDay(summary.peak.date) : "—"} />
                          </div>
                          <div className="rounded-3xl border border-[color:var(--prism-line)] bg-black/10 p-4">
                            <div className="text-sm font-black text-[color:var(--prism-ink)]">
                              {summary.last
                                ? `Последняя активность: ${formatActivityDay(summary.last.date)} · ${summary.last.attempts} попыток`
                                : "За период активных занятий не было"}
                            </div>
                            <p className="mt-1 text-xs leading-5 text-[color:var(--prism-muted)]">График ниже показывает последние дни без технических дат: подпись — день, длина — сколько было попыток.</p>
                          </div>
                          <div className="space-y-2">
                            {recentDays.map((day) => {
                              const width = Math.max(5, Math.round((day.attempts / max) * 100));
                              return (
                                <div key={day.date} className="parent-activity-row">
                                  <div className="w-16 shrink-0 text-xs font-black text-[color:var(--prism-muted)]">{formatActivityDay(day.date)}</div>
                                  <div className="parent-activity-track" aria-hidden="true">
                                    <div className="parent-activity-bar" style={{ width: `${width}%` }} />
                                  </div>
                                  <div className="w-20 text-right text-xs font-black text-[color:var(--prism-ink)]">{day.attempts} попыток</div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              )}
            </section>
          </section>
        </div>
        </div>
      </section>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/50 p-4">
      <div className="text-[10px] font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">{label}</div>
      <div className="mt-1 text-2xl font-black text-[color:var(--prism-ink)]">{value}</div>
    </div>
  );
}


function ActivityStat({ label, value, note }: { label: string; value: string | number; note: string }) {
  return (
    <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/50 p-3">
      <div className="text-[10px] font-black uppercase tracking-[0.16em] text-[color:var(--prism-muted)]">{label}</div>
      <div className="mt-1 text-xl font-black text-[color:var(--prism-ink)]">{value}</div>
      <div className="mt-1 text-xs text-[color:var(--prism-muted)]">{note}</div>
    </div>
  );
}
