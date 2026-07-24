"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, getToken, setToken } from "@/lib/api";

// === Types (Sprint 3) ===
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
  privacy_note: string;
};

export default function ParentDashboardPage() {
  const router = useRouter();
  const params = useParams();
  const studentId = Number(params.studentId);
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // Sprint 27: cookie auth.
    if (!studentId) return;
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId]);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      const data = await api.parentDashboard(studentId);
      setDash(data);
    } catch (e: any) {
      const status = e?.status;
      if (status === 401) {
        // Sprint 27: setToken removed
        router.push("/login");
        return;
      }
      setError(e?.body?.detail || "Ошибка загрузки дашборда");
    } finally {
      setBusy(false);
    }
  }

  function downloadPdf() {
    const token = getToken();
    if (!token) return;
    // Открываем в новой вкладке — браузер сам предложит «Сохранить как PDF»
    const url = `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/parents/students/${studentId}/dashboard.pdf`;
    // Используем iframe чтобы токен передать через Authorization (открыть в новой вкладке сложнее)
    // Проще: fetch и download через blob
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `dashboard-${studentId}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      })
      .catch(() => alert("Не удалось скачать отчёт"));
  }

  if (!dash) {
    return (
      <main className="mx-auto max-w-5xl p-6">
        {error && (
          <div className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">
            {error}
          </div>
        )}
        <div className="mt-4 text-sm text-slate-500">
          {busy ? "Загрузка дашборда…" : "Нет данных"}
        </div>
      </main>
    );
  }

  const s = dash.student;

  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="border-b border-slate-200 pb-3">
        <Link href="/parents" className="text-sm text-sky-600 hover:underline">
          ← К списку детей
        </Link>
        <div className="mt-1 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Дашборд: {s.display_name}</h1>
            <p className="mt-1 text-sm text-slate-600">
              Обновлено:{" "}
              {new Date(dash.generated_at).toLocaleString("ru-RU", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
          </div>
        </div>
      </header>

      {/* KPI карточки */}
      <section className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="Попыток всего" value={dash.total_attempts} />
        <Kpi label="Точность" value={`${Math.round(dash.accuracy * 100)}%`} />
        <Kpi
          label="Средний mastery"
          value={`${Math.round(dash.average_mastery * 100)}%`}
        />
        <Kpi
          label="К повторению"
          value={dash.due_for_review_count}
          color={dash.due_for_review_count > 0 ? "amber" : "emerald"}
        />
      </section>

      {/* Streak */}
      <section className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi
          label="🔥 Сегодняшняя серия"
          value={`${dash.streak.current_streak_days}д`}
        />
        <Kpi
          label="🏆 Лучшая серия"
          value={`${dash.streak.longest_streak_days}д`}
        />
        <Kpi
          label="📅 Активных дней"
          value={dash.streak.total_active_days}
        />
        <Kpi
          label="⏱ Последние 7 дней"
          value={`${dash.time_stats.last_7_days} попыток`}
        />
      </section>

      {/* График активности */}
      <section className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold">📈 Активность за 30 дней</h2>
        <div className="mt-3 flex h-32 items-end gap-1">
          {dash.daily_activity_30d.map((d) => {
            const max = Math.max(
              ...dash.daily_activity_30d.map((x) => x.attempts),
              1
            );
            const h = Math.max(2, Math.round((d.attempts / max) * 100));
            return (
              <div
                key={d.date}
                className="flex flex-1 flex-col items-center gap-1"
                title={`${d.date}: ${d.attempts} попыток`}
              >
                <div
                  className={`w-full rounded-t ${
                    d.attempts > 0 ? "bg-sky-500" : "bg-slate-200"
                  }`}
                  style={{ height: `${h}px` }}
                />
              </div>
            );
          })}
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-slate-500">
          <span>{dash.daily_activity_30d[0]?.date.slice(5)}</span>
          <span>
            сегодня: {dash.daily_activity_30d.at(-1)?.date.slice(5)}
          </span>
        </div>
      </section>

      {/* Mastery по предметам */}
      <section className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold">📚 Mastery по предметам</h2>
        <div className="mt-3 space-y-2">
          {dash.subject_mastery.map((sm) => (
            <SubjectBar key={sm.subject_id} sm={sm} />
          ))}
          {dash.subject_mastery.length === 0 && (
            <p className="text-sm text-slate-500">Нет данных</p>
          )}
        </div>
      </section>

      {/* Слабые темы */}
      {dash.weak_topics.length > 0 && (
        <section className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <h2 className="text-base font-semibold text-amber-900">
            ⚠ Слабые темы (mastery &lt; 60%)
          </h2>
          <ul className="mt-2 space-y-1 text-sm">
            {dash.weak_topics.slice(0, 5).map((w) => (
              <li
                key={w.topic_id}
                className="flex items-center justify-between"
              >
                <Link
                  href={`/topics/${w.topic_id}`}
                  className="text-amber-800 hover:underline"
                >
                  {w.subject_name}: {w.topic_name}
                </Link>
                <span className="text-amber-700">
                  {Math.round(w.mastery * 100)}%
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Типичные ошибки */}
      {dash.top_mistakes.length > 0 && (
        <section className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4">
          <h2 className="text-base font-semibold text-rose-900">
            ❗ Типичные ошибки
          </h2>
          <ul className="mt-2 space-y-1 text-sm">
            {dash.top_mistakes.slice(0, 5).map((m, i) => (
              <li
                key={i}
                className="flex items-center justify-between rounded bg-white p-2"
              >
                <span>
                  <span className="text-rose-700">{m.mistake_type}:</span>{" "}
                  {m.topic_name}
                </span>
                <span className="rounded bg-rose-100 px-2 py-0.5 text-xs text-rose-800">
                  ×{m.count}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-4 rounded-md bg-amber-50 p-3 text-xs text-amber-900">
        🔒 {dash.privacy_note}
      </section>
    </main>
  );
}

function Kpi({
  label,
  value,
  color = "slate",
}: {
  label: string;
  value: string | number;
  color?: "slate" | "emerald" | "amber";
}) {
  const colors = {
    slate: "border-slate-200 bg-white",
    emerald: "border-emerald-200 bg-emerald-50",
    amber: "border-amber-200 bg-amber-50",
  };
  return (
    <div className={`rounded-xl border p-4 shadow-sm ${colors[color]}`}>
      <div className="text-xs uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
    </div>
  );
}

function SubjectBar({ sm }: { sm: SubjectMastery }) {
  const masteryPct = Math.round(sm.avg_mastery * 100);
  const accuracyPct = Math.round(sm.accuracy * 100);
  const color =
    masteryPct >= 75
      ? "bg-emerald-500"
      : masteryPct >= 50
        ? "bg-amber-500"
        : "bg-rose-500";

  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{sm.subject_name}</span>
        <span className="text-xs text-slate-500">
          {sm.topics_attempted}/{sm.topics_total} тем · точность {accuracyPct}%
        </span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-full ${color}`}
          style={{ width: `${masteryPct}%` }}
        />
      </div>
    </div>
  );
}
