"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Subject, Topic, User } from "@/types";
import Header from "@/components/Header";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export default function SubjectPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const subjectId = Number(params?.id);

  const [user, setUser] = useState<User | null>(null);
  const [subject, setSubject] = useState<Subject | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
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
        if (!currentSubject) {
          setError("Предмет не найден");
          return;
        }

        const loadedTopics = await api.subjectTopics(subjectId);
        if (!cancelled) setTopics(loadedTopics);
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
          router.push("/login");
          return;
        }
        setError("Не удалось загрузить темы. Проверь соединение и попробуй ещё раз.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [subjectId, router]);

  return (
    <main className="premium-shell">
      <Header user={user} backHref="/subjects" backLabel="Все предметы" title={subject ? `${subject.icon || "📘"} ${subject.name}` : "Предмет"} />

      <section className="premium-container px-2 py-8 sm:px-4 sm:py-10">
        <div className="premium-hero p-6 sm:p-9 lg:p-12">
          <div className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-end">
            <div>
              <div className="premium-kicker">Learning Route</div>
              <h1 className="premium-title mt-5 text-5xl font-black sm:text-6xl lg:text-7xl">
                {subject?.name || "Загружаем предмет…"}
              </h1>
              {subject?.description && <p className="premium-copy mt-5 max-w-2xl text-lg">{subject.description}</p>}
            </div>
            <div className="premium-panel p-5 text-white">
              <div className="grid grid-cols-2 gap-3">
                <StatusMetric label="Тем" value={topics.length || "—"} />
                <StatusMetric label="Статус" value={subject?.mvp_status === "mvp_ready" ? "Ready" : "Preview"} />
                <StatusMetric label="RAG" value={subject?.rag_ready ? "ON" : "OFF"} tone={subject?.rag_ready ? "good" : "warn"} />
                <StatusMetric label="Practice" value={subject?.practice_ready ? "ON" : "Preview"} tone={subject?.practice_ready ? "good" : "warn"} />
              </div>
              {subject && (
                <div className={`mt-4 rounded-2xl border p-4 text-sm ${subject.mvp_status === "mvp_ready" ? "border-emerald-300/30 bg-emerald-300/10 text-emerald-100" : "border-amber-300/30 bg-amber-300/10 text-amber-100"}`}>
                  <b>{subject.mvp_status === "mvp_ready" ? "MVP-ready." : "Preview-предмет."}</b> {subject.support_note}
                </div>
              )}
            </div>
          </div>
        </div>

        {loading && <Card variant="flat" padding="lg" className="mt-6 text-sm text-[#4a3d5d]">Загружаем темы…</Card>}
        {error && !loading && <Card variant="flat" padding="lg" className="mt-6 border-danger/30 bg-danger/5 text-sm text-danger">{error}</Card>}
        {!loading && !error && topics.length === 0 && <Card variant="flat" padding="lg" className="mt-6 text-sm text-[#4a3d5d]">В этом предмете пока нет тем.</Card>}

        <section className="mt-8">
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <div className="premium-kicker">Topic Deck</div>
              <h2 className="premium-title mt-3 text-3xl font-black sm:text-5xl">Маршрут тем</h2>
            </div>
            <Badge variant={subject?.mvp_status === "mvp_ready" ? "success" : "warning"} size="lg">
              {subject?.mvp_status === "mvp_ready" ? "MVP-ready" : "Preview"}
            </Badge>
          </div>

          <ol className="grid gap-4 lg:grid-cols-2">
            {topics.map((topic, index) => (
              <li key={topic.id}>
                <Link href={`/topics/${topic.id}`} className="group block">
                  <article className="premium-tile flex h-full items-center justify-between gap-5 p-5 transition-modern">
                    <div className="flex items-start gap-4">
                      <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl brand-gradient text-sm font-black text-white shadow-glow">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <div>
                        <h3 className="text-xl font-black tracking-tight text-[#171022] transition-modern group-hover:text-brand-600">
                          {topic.name}
                        </h3>
                        {topic.description && <p className="mt-1 line-clamp-2 text-sm text-[#4a3d5d]">{topic.description}</p>}
                      </div>
                    </div>
                    <Badge variant={difficultyVariant(topic.difficulty)} size="sm">
                      {topic.difficulty}/5
                    </Badge>
                  </article>
                </Link>
              </li>
            ))}
          </ol>
        </section>
      </section>
    </main>
  );
}

function StatusMetric({ label, value, tone = "neutral" }: { label: string; value: string | number; tone?: "neutral" | "good" | "warn" }) {
  return (
    <div className="rounded-2xl border border-white/12 bg-white/8 p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-white/50">{label}</div>
      <div className={`mt-1 text-xl font-black ${tone === "good" ? "text-[#14d87a]" : tone === "warn" ? "text-[#ffb000]" : "text-white"}`}>{value}</div>
    </div>
  );
}

function difficultyVariant(difficulty: number): "success" | "info" | "warning" | "danger" {
  if (difficulty <= 2) return "success";
  if (difficulty <= 3) return "info";
  if (difficulty <= 4) return "warning";
  return "danger";
}
