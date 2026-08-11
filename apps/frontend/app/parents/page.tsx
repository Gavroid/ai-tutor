"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

type LinkedStudent = {
  student_id: number;
  display_name: string;
  email: string;
  linked_at: string;
};

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

export default function ParentsPage() {
  const router = useRouter();
  const [children, setChildren] = useState<LinkedStudent[]>([]);
  const [invite, setInvite] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyInvite, setBusyInvite] = useState(false);
  const [loadingChildren, setLoadingChildren] = useState(true);

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  function refresh() {
    setLoadingChildren(true);
    api
      .parentsChildren()
      .then((linkedChildren) => {
        setChildren(linkedChildren);
        const saved = typeof window !== "undefined" ? localStorage.getItem("ai-tutor:parent:selected") : null;
        if (saved && linkedChildren.some((child) => String(child.student_id) === saved)) {
          setSelectedId(Number(saved));
        } else if (linkedChildren.length > 0) {
          setSelectedId(linkedChildren[0].student_id);
        } else {
          setSelectedId(null);
          setOverview(null);
        }
      })
      .catch(() => setError("Не удалось загрузить список детей"))
      .finally(() => setLoadingChildren(false));
  }

  function pickChild(id: number) {
    setSelectedId(id);
    try {
      localStorage.setItem("ai-tutor:parent:selected", String(id));
    } catch {
      // ignore storage issues
    }
  }

  useEffect(() => {
    if (!selectedId) return;
    api.parentsOverview(selectedId).then(setOverview).catch(() => setOverview(null));
  }, [selectedId]);

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
    <main className="prism-shell min-h-dvh py-4 sm:py-7">
      <section className="prism-frame">
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
              <button onClick={createInvite} disabled={busyInvite} className="prism-action primary mt-5 w-full">
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
                  {children.map((child) => (
                    <div key={child.student_id} className={`rounded-3xl border p-3 ${selectedId === child.student_id ? "border-[color:var(--prism-accent)] bg-[color:var(--prism-panel-solid)]/55 shadow-glow" : "border-[color:var(--prism-line)] bg-black/10"}`}>
                      <button onClick={() => pickChild(child.student_id)} className="w-full text-left">
                        <div className="font-black text-[color:var(--prism-ink)]">{child.display_name}</div>
                        <div className="mt-1 text-xs text-[color:var(--prism-muted)]">Привязан: {new Date(child.linked_at).toLocaleDateString("ru-RU")}</div>
                      </button>
                      <Link href={`/parent/dashboard/${child.student_id}`} className="prism-action mt-3 w-full">Открыть дашборд</Link>
                    </div>
                  ))}
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

                  <div className="prism-card pad">
                    <div className="prism-kicker">Активность</div>
                    {overview.daily_activity.length === 0 ? (
                      <p className="mt-4 text-sm text-[color:var(--prism-muted)]">Первые занятия ещё не появились.</p>
                    ) : (
                      <div className="mt-5 flex h-32 items-end gap-1.5">
                        {overview.daily_activity.map((day) => {
                          const max = Math.max(...overview.daily_activity.map((item) => item.attempts), 1);
                          const height = Math.max(4, Math.round((day.attempts / max) * 100));
                          return <div key={day.date} title={`${day.date}: ${day.attempts}`} className={`flex-1 rounded-t-lg ${day.attempts > 0 ? "bg-[color:var(--prism-accent)]" : "bg-[color:var(--prism-line)]"}`} style={{ height: `${height}%` }} />;
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </section>
          </section>
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
