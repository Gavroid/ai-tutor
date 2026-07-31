"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { TopicReadiness, User } from "@/types";

const PRIORITIES = ["", "P0", "P1", "P2"] as const;
type PriorityFilter = (typeof PRIORITIES)[number];

const BADGE_CLASS: Record<string, string> = {
  P0: "bg-rose-100 text-rose-800",
  P1: "bg-amber-100 text-amber-800",
  P2: "bg-slate-100 text-slate-700",
  "Smoke OK": "bg-emerald-100 text-emerald-800",
  Verified: "bg-sky-100 text-sky-800",
  TODO: "bg-slate-100 text-slate-700",
  OK: "bg-emerald-100 text-emerald-800",
};

function badge(value: string) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${BADGE_CLASS[value] || "bg-slate-100 text-slate-700"}`}>
      {value}
    </span>
  );
}

export default function TeacherTopicsReadinessPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [rows, setRows] = useState<TopicReadiness[]>([]);
  const [priority, setPriority] = useState<PriorityFilter>("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.me().then(setUser).catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setBusy(true);
    setError(null);
    api
      .teacherTopicReadiness({ subject_id: 3, priority: priority || undefined })
      .then((data) => {
        if (!cancelled) setRows(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Ошибка загрузки readiness");
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [user, priority]);

  const summary = useMemo(() => {
    return rows.reduce(
      (acc, row) => {
        acc.topics += 1;
        acc.materials += row.material_count;
        acc.chunks += row.chunk_count;
        acc.fallbacks += row.fallback_count;
        acc.followups += row.followup_count;
        return acc;
      },
      { topics: 0, materials: 0, chunks: 0, fallbacks: 0, followups: 0 },
    );
  }, [rows]);

  return (
    <main className="mx-auto max-w-7xl p-6">
      <header className="border-b border-slate-200 pb-3">
        <Link href="/teacher" className="text-sm text-sky-600 hover:underline">
          ← Учительская
        </Link>
        <div className="mt-1 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold">Готовность тем</h1>
            <p className="mt-1 text-sm text-slate-600">
              Read-only Stage 4.1 dashboard: материалы, RAG chunks, fallback и follow-up coverage.
            </p>
          </div>
          <Link
            href="/teacher/generate"
            className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
          >
            + Материал
          </Link>
        </div>
      </header>

      <section className="mt-4 grid gap-3 sm:grid-cols-5">
        <Metric label="Темы" value={summary.topics} />
        <Metric label="Материалы" value={summary.materials} />
        <Metric label="RAG chunks" value={summary.chunks} />
        <Metric label="Fallback" value={summary.fallbacks} />
        <Metric label="Follow-up" value={summary.followups} />
      </section>

      <div className="mt-4 flex flex-wrap gap-2">
        {PRIORITIES.map((value) => (
          <button
            key={value || "all"}
            type="button"
            onClick={() => setPriority(value)}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              priority === value ? "bg-sky-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {value || "Все"}
          </button>
        ))}
      </div>

      {error && <div className="mt-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
      {busy && <div className="mt-4 text-sm text-slate-500">Загрузка…</div>}

      {!busy && !error && (
        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">Тема</th>
                <th className="px-3 py-2">Priority</th>
                <th className="px-3 py-2">Материалы</th>
                <th className="px-3 py-2">Chunks</th>
                <th className="px-3 py-2">Fallback</th>
                <th className="px-3 py-2">Follow-up</th>
                <th className="px-3 py-2">Explain</th>
                <th className="px-3 py-2">Practice</th>
                <th className="px-3 py-2">Sources</th>
                <th className="px-3 py-2">Manual</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => (
                <tr key={row.topic_id} className="hover:bg-slate-50">
                  <td className="max-w-md px-3 py-2">
                    <div className="font-semibold text-slate-900">
                      <Link href={`/teacher/topics/${row.topic_id}`} className="text-sky-700 hover:underline">
                        #{row.topic_id} · {row.topic_name}
                      </Link>
                    </div>
                    <div className="text-xs text-slate-500">{row.section_name}</div>
                  </td>
                  <td className="px-3 py-2">{badge(row.priority)}</td>
                  <td className="px-3 py-2 tabular-nums">{row.material_count}</td>
                  <td className="px-3 py-2 tabular-nums">{row.chunk_count}</td>
                  <td className="px-3 py-2 tabular-nums">{row.fallback_count}</td>
                  <td className="px-3 py-2 tabular-nums">{row.followup_count}</td>
                  <td className="px-3 py-2">{badge(row.explain_status)}</td>
                  <td className="px-3 py-2">{badge(row.practice_status)}</td>
                  <td className="px-3 py-2">{badge(row.source_status)}</td>
                  <td className="px-3 py-2">{badge(row.manual_qa_status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-bold text-slate-900">{value}</div>
    </div>
  );
}
