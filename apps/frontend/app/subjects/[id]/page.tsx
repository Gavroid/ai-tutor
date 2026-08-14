"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { MathTopicPlan, Subject, Topic, User } from "@/types";
import Header from "@/components/Header";

export default function SubjectPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const subjectId = Number(params?.id);

  const [user, setUser] = useState<User | null>(null);
  const [subject, setSubject] = useState<Subject | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [routePlan, setRoutePlan] = useState<MathTopicPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!subjectId || Number.isNaN(subjectId)) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await api.me();
        if (cancelled) return;
        setUser(me);
        const all = await api.subjects();
        if (cancelled) return;
        const currentSubject = all.find((x) => x.id === subjectId) ?? null;
        setSubject(currentSubject);
        if (!currentSubject) { setError("Предмет не найден"); return; }
        const [loadedTopics, loadedRoutePlan] = await Promise.all([
          api.subjectTopics(subjectId),
          api.subjectRoutePlan(subjectId).catch(() => []),
        ]);
        if (!cancelled) {
          setTopics(loadedTopics);
          setRoutePlan(loadedRoutePlan);
        }
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) { router.push("/login"); return; }
        setError("Не удалось загрузить темы. Проверь соединение и попробуй ещё раз.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [subjectId, router]);

  const routeByTopic = new Map(routePlan.map((item) => [item.topic_id, item]));
  const routeSummary = {
    base: routePlan.filter((item) => item.tier === "base").length,
    medium: routePlan.filter((item) => item.tier === "medium").length,
    hard: routePlan.filter((item) => item.tier === "hard").length,
    checkpoints: routePlan.filter((item) => item.checkpoint).length,
  };

  return (
    <main className="prism-shell">
      <Header user={user} backHref="/subjects" backLabel="Все предметы" title={subject ? `${subject.icon || "📘"} ${subject.name}` : "Предмет"} />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer prism-hero-grid subject-compact-hero">
            <section>
              <div className="prism-kicker">Subject Object · Route Map</div>
              <h1 className="prism-title"><span className="accent">{subject?.icon || "📘"}</span> {subject?.name || "Загружаем"}</h1>
              {subject?.description && <p className="prism-copy">{subject.description}</p>}
            </section>
            <aside className="prism-card pad glow">
              <div className="text-xs font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">Readiness Panel</div>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <Readiness label="Тем" value={topics.length || "—"} />
                <Readiness label="Статус" value={subject?.mvp_status === "mvp_ready" ? "Ready" : "Preview"} />
                <Readiness label="RAG" value={subject?.rag_ready ? "ON" : "OFF"} hot={!!subject?.rag_ready} />
                <Readiness label="Practice" value={subject?.practice_ready ? "ON" : "Preview"} hot={!!subject?.practice_ready} />
                {routePlan.length > 0 && <Readiness label="Маршрут" value={`${routePlan.length}/42`} hot />}
                {routePlan.length > 0 && <Readiness label="Контроль" value={routeSummary.checkpoints} hot />}
              </div>
              {subject && <p className="mt-5 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-4 text-sm text-[color:var(--prism-muted)]"><b>{subject.mvp_status === "mvp_ready" ? "MVP-ready." : "Preview-предмет."}</b> {subject.support_note}</p>}
            </aside>
          </div>

          <section className="prism-layer px-4 pb-5 lg:px-7 lg:pb-7">
            {loading && <div className="prism-card pad">Загружаем темы…</div>}
            {error && !loading && <div className="prism-card pad text-danger">{error}</div>}
            {!loading && !error && topics.length === 0 && <div className="prism-card pad">В этом предмете пока нет тем.</div>}

            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="prism-kicker">Timeline</div>
                <h2 className="mt-2 text-3xl font-black tracking-[-0.05em] sm:text-5xl">Маршрут тем</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className={`prism-pill ${subject?.mvp_status === "mvp_ready" ? "active" : ""}`}>{subject?.mvp_status === "mvp_ready" ? "MVP-ready" : "Preview"}</span>
                {routePlan.length > 0 && <span className="prism-pill active">Base {routeSummary.base} · Medium {routeSummary.medium} · Hard {routeSummary.hard}</span>}
              </div>
            </div>

            <ol className="grid gap-3 xl:grid-cols-2">
              {topics.map((topic, index) => {
                const route = routeByTopic.get(topic.id);
                return (
                <li key={topic.id}>
                  <Link href={`/topics/${topic.id}`} className="prism-card pad flex min-h-[124px] flex-col gap-3 hover:border-[color:var(--prism-accent)] sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-start gap-4">
                      <span className="prism-mark flex shrink-0 items-center justify-center text-sm font-black text-white">{String(route?.order ?? index + 1).padStart(2, "0")}</span>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-lg font-black tracking-[-0.035em]">{topic.name}</h3>
                          {route?.checkpoint && <span className="prism-pill active">Контроль</span>}
                        </div>
                        {route?.focus && <p className="mt-1 text-sm text-[color:var(--prism-muted)]">Фокус: {route.focus}</p>}
                        {topic.description && <p className="mt-1 line-clamp-2 text-sm text-[color:var(--prism-muted)]">{topic.description}</p>}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2 sm:justify-end">
                      {route?.tier && <span className="prism-pill">{route.tier}</span>}
                      <span className="prism-pill">{topic.difficulty}/5</span>
                    </div>
                  </Link>
                </li>
              );})}
            </ol>
          </section>
        </div>
      </section>
    </main>
  );
}

function Readiness({ label, value, hot = false }: { label: string; value: string | number; hot?: boolean }) {
  return <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/50 p-4"><div className="text-[10px] font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">{label}</div><div className={`mt-1 text-2xl font-black ${hot ? "text-[color:var(--prism-green)]" : ""}`}>{value}</div></div>;
}
