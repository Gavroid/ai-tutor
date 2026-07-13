"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, getToken } from "@/lib/api";

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

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    refresh();
  }, [router]);

  function refresh() {
    api
      .parentsChildren()
      .then((c) => {
        setChildren(c);
        // Sprint 9.2: восстанавливаем выбор из localStorage
        const saved = typeof window !== "undefined" ? localStorage.getItem("ai-tutor:parent:selected") : null;
        if (saved && c.some((x) => String(x.student_id) === saved)) {
          setSelectedId(Number(saved));
        } else if (c.length > 0 && !selectedId) {
          setSelectedId(c[0].student_id);
        }
      })
      .catch(() => {});
  }

  function pickChild(id: number) {
    setSelectedId(id);
    // Sprint 9.2: сохраняем выбор
    try {
      localStorage.setItem("ai-tutor:parent:selected", String(id));
    } catch {
      // quota или SSR
    }
  }

  useEffect(() => {
    if (selectedId) {
      api.parentsOverview(selectedId).then(setOverview).catch(() => setOverview(null));
    }
  }, [selectedId]);

  async function createInvite() {
    try {
      const r = await api.parentsInvite();
      setInvite(r.code);
    } catch (e) {
      setError("Не удалось создать код");
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-6">
      <header className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div>
          <Link href="/subjects" className="text-sm text-sky-600 hover:underline">
            ← На главную
          </Link>
          <h1 className="mt-1 text-2xl font-bold">Родительский кабинет</h1>
          <p className="text-sm text-slate-600">
            Отчёты по занятиям ребёнка. Переписка с AI остаётся приватной.
          </p>
        </div>
      </header>

      {error && <div className="mt-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

      <section className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Привязать ребёнка</h2>
          <button
            onClick={createInvite}
            className="rounded-md bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-500"
          >
            Создать код
          </button>
        </div>
        {invite && (
          <div className="mt-3 rounded-md bg-amber-50 p-3 text-sm">
            <div className="text-amber-900">Код для ребёнка (ввести в его личном кабинете):</div>
            <div className="mt-1 font-mono text-lg font-bold tracking-wider text-amber-900">{invite}</div>
          </div>
        )}
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Привязанные дети</h2>
        {children.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">Пока никого нет. Создайте код выше.</p>
        ) : (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {children.map((c) => (
              <div
                key={c.student_id}
                className={`flex items-center gap-1 rounded-lg border px-1 py-1 ${
                  selectedId === c.student_id
                    ? "border-sky-500 bg-sky-50 text-sky-900"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
              >
                <button
                  onClick={() => pickChild(c.student_id)}
                  className="rounded-md px-2 py-1 text-sm"
                >
                  {c.display_name}
                </button>
                <Link
                  href={`/parent/dashboard/${c.student_id}`}
                  className="rounded-md bg-sky-100 px-2 py-1 text-xs font-medium text-sky-800 hover:bg-sky-200"
                  title="Расширенный дашборд"
                >
                  📊
                </Link>
              </div>
            ))}
          </div>
        )}
      </section>

      {overview && (
        <section className="mt-6 space-y-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Решено заданий" value={overview.total_attempts} />
            <Stat label="Правильных" value={overview.correct_attempts} />
            <Stat label="Точность" value={`${Math.round(overview.accuracy * 100)}%`} />
            <Stat label="Средний mastery" value={`${Math.round(overview.average_mastery * 100)}%`} />
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-base font-semibold">Слабые темы</h3>
            {overview.weak_topics.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">Нет слабых тем — отлично!</p>
            ) : (
              <ul className="mt-2 space-y-1 text-sm">
                {overview.weak_topics.map((w) => (
                  <li key={w.topic_id} className="flex items-center justify-between">
                    <span>
                      <span className="text-slate-500">{w.subject_name}:</span> {w.topic_name}
                    </span>
                    <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs text-rose-800">
                      {Math.round(w.mastery * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-base font-semibold">Активность (последние дни)</h3>
            {overview.daily_activity.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">Ребёнок ещё не начинал заниматься.</p>
            ) : (
              <div className="mt-3 flex items-end gap-1">
                {overview.daily_activity.map((d) => {
                  const max = Math.max(...overview.daily_activity.map((x) => x.attempts), 1);
                  const h = Math.max(8, Math.round((d.attempts / max) * 60));
                  return (
                    <div key={d.date} className="flex flex-1 flex-col items-center gap-1">
                      <div
                        className="w-full rounded-t bg-sky-500"
                        style={{ height: `${h}px` }}
                        title={`${d.date}: ${d.attempts}`}
                      />
                      <div className="text-[10px] text-slate-500">{d.date.slice(5)}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-600">
            🔒 {overview.privacy_note}
          </div>
        </section>
      )}
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
    </div>
  );
}