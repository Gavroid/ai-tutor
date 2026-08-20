"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Header from "@/components/Header";
import type { LearningAnalytics, User } from "@/types";

export default function TeacherAnalyticsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [analytics, setAnalytics] = useState<LearningAnalytics | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.me().then(setUser).catch(() => {
      router.push("/login");
    });
  }, [router]);

  useEffect(() => {
    if (!user) return;
    setBusy(true);
    setError(null);
    api.learningAnalytics(30)
      .then(setAnalytics)
      .catch((e: any) => setError(e?.body?.detail || "Ошибка загрузки аналитики"))
      .finally(() => setBusy(false));
  }, [user]);

  return (
    <main className="prism-shell teacher-console teacher-analytics-console min-h-dvh">
      <Header user={user} backHref="/teacher" title="Где обучение проседает" />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer p-5 lg:p-10">
            <section className="border-b border-[color:var(--prism-line)] pb-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <Link href="/teacher" className="prism-action w-fit px-4 py-2 text-sm">
                    ← К материалам
                  </Link>
                  <h1 className="mt-4 text-2xl font-bold text-[color:var(--prism-ink)]">Где обучение проседает</h1>
                  <p className="prism-copy mt-2 max-w-3xl">
                    Агрегаты по темам и предметам — без сырого AI-чата ученика.
                  </p>
                </div>
                <Link href="/teacher/topics" className="prism-action">
                  Готовность тем
                </Link>
              </div>
            </section>

            {error && <div className="mt-5 rounded-2xl border border-rose-400/30 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</div>}
            {busy && <div className="mt-5 text-sm text-[color:var(--prism-muted)]">Загрузка аналитики…</div>}

            {!busy && analytics && (
              <section className="teacher-analytics-card mt-5" aria-labelledby="teacher-analytics-heading">
                <div className="teacher-analytics-hero">
                  <div className="teacher-analytics-copy">
                    <div className="prism-kicker teacher-analytics-kicker">Learning Analytics</div>
                    <h2 id="teacher-analytics-heading" className="teacher-analytics-title">Где обучение проседает</h2>
                    <p className="teacher-analytics-subtitle">Агрегаты по темам и предметам — без сырого AI-чата ученика.</p>
                  </div>
                  <div className="teacher-analytics-focus" aria-label="Слабых тем">
                    <span className="teacher-analytics-focus-label">Слабых тем</span>
                    <strong>{analytics.totals.weak_topics}</strong>
                    <span className="teacher-analytics-focus-note">нужны повторение и короткая практика</span>
                  </div>
                </div>
                <div className="teacher-analytics-metrics">
                  <MiniMetric label="Попыток" value={analytics.totals.attempts} className="teacher-analytics-metric" />
                  <MiniMetric label="Верно" value={analytics.totals.correct} className="teacher-analytics-metric" />
                  <MiniMetric label="Точность" value={Math.round(analytics.totals.accuracy * 100)} className="teacher-analytics-metric" />
                  <MiniMetric label="Mastery" value={Math.round(analytics.totals.average_mastery * 100)} className="teacher-analytics-metric" />
                </div>
                <div className="teacher-analytics-grid">
                  <div className="teacher-analytics-panel">
                    <h3>Предметы</h3>
                    <div className="teacher-analytics-list">
                      {analytics.subjects.slice(0, 8).map((subject) => (
                        <div key={subject.subject_id} className="teacher-analytics-row">
                          <span>{subject.subject_name}</span>
                          <small>{subject.attempts} попыток · {Math.round(subject.accuracy * 100)}%</small>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="teacher-analytics-panel">
                    <h3>Слабые темы</h3>
                    <div className="teacher-analytics-list">
                      {analytics.weak_topics.length === 0 && <p className="teacher-analytics-empty">Пока слабых тем нет.</p>}
                      {analytics.weak_topics.slice(0, 8).map((topic) => (
                        <Link key={topic.topic_id} href={`/topics/${topic.topic_id}`} className="teacher-analytics-row teacher-analytics-link">
                          <span>{topic.topic_name}</span>
                          <small>{topic.subject_name} · mastery {Math.round(topic.mastery_score * 100)}% · попыток {topic.attempts_count}</small>
                        </Link>
                      ))}
                    </div>
                  </div>
                </div>
              </section>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

function MiniMetric({ label, value, className = "" }: { label: string; value: number; className?: string }) {
  return (
    <div className={`rounded-3xl border border-[color:var(--prism-line)] bg-black/10 p-3 ${className}`.trim()}>
      <div className="text-[10px] font-black uppercase tracking-[0.16em] text-[color:var(--prism-muted)]">{label}</div>
      <div className="mt-1 text-xl font-black text-[color:var(--prism-ink)]">{value}</div>
    </div>
  );
}
