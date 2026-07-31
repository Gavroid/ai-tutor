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
    <main className="min-h-screen bg-app">
      <Header
        user={user}
        backHref="/subjects"
        backLabel="Все предметы"
        title={subject ? `${subject.icon || "📘"} ${subject.name}` : "Предмет"}
      />

      <section className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
        <Card variant="glass" padding="lg" className="mb-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-medium text-brand-500">Учебный маршрут</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-fg">
                {subject?.name || "Загружаем предмет…"}
              </h2>
              {subject?.description && (
                <p className="mt-2 max-w-2xl text-sm text-fg-muted">{subject.description}</p>
              )}
            </div>
            <Badge variant="outline" size="lg">
              {topics.length || 0} тем
            </Badge>
          </div>
          {subject && subject.mvp_status !== "mvp_ready" && (
            <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              <b>Preview-предмет.</b> {subject.support_note || "Темы доступны для навигации, но материалы и источники ещё не подтверждены."}
            </div>
          )}
          {subject && subject.mvp_status === "mvp_ready" && (
            <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
              <b>MVP-ready.</b> {subject.support_note}
            </div>
          )}
        </Card>

        {loading && (
          <Card variant="flat" padding="lg" className="text-sm text-fg-muted">
            Загружаем темы…
          </Card>
        )}

        {error && !loading && (
          <Card variant="flat" padding="lg" className="border-danger/30 bg-danger/5 text-sm text-danger">
            {error}
          </Card>
        )}

        {!loading && !error && topics.length === 0 && (
          <Card variant="flat" padding="lg" className="text-sm text-fg-muted">
            В этом предмете пока нет тем.
          </Card>
        )}

        <ol className="grid gap-3">
          {topics.map((topic, index) => (
            <li key={topic.id}>
              <Link href={`/topics/${topic.id}`} className="group block">
                <Card variant="elevated" padding="md" interactive className="flex items-center justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-surface-2 text-sm font-semibold text-fg-muted">
                      {index + 1}
                    </span>
                    <div>
                      <h3 className="font-semibold text-fg transition-modern group-hover:text-brand-500">
                        {topic.name}
                      </h3>
                      {topic.description && (
                        <p className="mt-1 line-clamp-2 text-sm text-fg-muted">{topic.description}</p>
                      )}
                    </div>
                  </div>
                  <Badge variant={difficultyVariant(topic.difficulty)} size="sm">
                    {topic.difficulty}/5
                  </Badge>
                </Card>
              </Link>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

function difficultyVariant(difficulty: number): "success" | "info" | "warning" | "danger" {
  if (difficulty <= 2) return "success";
  if (difficulty <= 3) return "info";
  if (difficulty <= 4) return "warning";
  return "danger";
}
