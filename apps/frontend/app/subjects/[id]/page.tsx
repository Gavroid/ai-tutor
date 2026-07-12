"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, getToken, setToken } from "@/lib/api";
import type { Subject, Topic } from "@/types";

export default function SubjectPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const subjectId = Number(params?.id);

  const [subject, setSubject] = useState<Subject | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    if (!subjectId || Number.isNaN(subjectId)) return;

    (async () => {
      try {
        const all = await api.subjects();
        const s = all.find((x) => x.id === subjectId) ?? null;
        setSubject(s);
        const t = await api.subjectTopics(subjectId);
        setTopics(t);
      } catch (e) {
        setError("Не удалось загрузить темы");
      } finally {
        setLoading(false);
      }
    })();
  }, [subjectId, router]);

  return (
    <main className="mx-auto max-w-4xl p-6">
      <header className="border-b border-slate-200 pb-4">
        <Link href="/subjects" className="text-sm text-sky-600 hover:underline">
          ← Все предметы
        </Link>
        <h1 className="mt-2 text-2xl font-bold">
          {subject?.icon} {subject?.name || "Предмет"}
        </h1>
        {subject?.description && <p className="text-sm text-slate-600">{subject.description}</p>}
      </header>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Темы</h2>
        {loading && <p className="mt-3 text-sm text-slate-500">Загружаем…</p>}
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
        {!loading && topics.length === 0 && (
          <p className="mt-3 text-sm text-slate-500">В этом предмете пока нет тем.</p>
        )}
        <ol className="mt-4 space-y-2">
          {topics.map((t, i) => (
            <li key={t.id}>
              <Link
                href={`/topics/${t.id}`}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 hover:border-sky-300"
              >
                <div className="flex items-start gap-3">
                  <span className="inline-block w-7 text-center text-sm font-mono text-slate-400">
                    {i + 1}
                  </span>
                  <span className="font-medium">{t.name}</span>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs ${difficultyClass(t.difficulty)}`}>
                  сложность {t.difficulty}/5
                </span>
              </Link>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

function difficultyClass(d: number): string {
  if (d <= 2) return "bg-emerald-100 text-emerald-800";
  if (d <= 3) return "bg-sky-100 text-sky-800";
  if (d <= 4) return "bg-amber-100 text-amber-800";
  return "bg-rose-100 text-rose-800";
}