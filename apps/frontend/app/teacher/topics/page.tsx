"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Header from "@/components/Header";
import type { TopicReadiness, User } from "@/types";

const PRIORITIES = ["", "P0", "P1", "P2"] as const;
type PriorityFilter = (typeof PRIORITIES)[number];

export default function TeacherTopicsReadinessPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [rows, setRows] = useState<TopicReadiness[]>([]);
  const [priority, setPriority] = useState<PriorityFilter>("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.me().then(setUser).catch(() => router.push("/login")); }, [router]);
  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setBusy(true);
    setError(null);
    api.teacherTopicReadiness({ subject_id: 3, priority: priority || undefined })
      .then((data) => { if (!cancelled) setRows(data); })
      .catch((err: unknown) => { if (!cancelled) setError(err instanceof Error ? err.message : "Ошибка загрузки readiness"); })
      .finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; };
  }, [user, priority]);

  const summary = rows.reduce((acc, row) => {
    acc.topics += 1; acc.materials += row.material_count; acc.chunks += row.chunk_count; acc.fallbacks += row.fallback_count; acc.followups += row.followup_count; return acc;
  }, { topics: 0, materials: 0, chunks: 0, fallbacks: 0, followups: 0 });

  return (
    <main className="prism-shell teacher-console min-h-dvh">
      <Header user={user} backHref="/teacher" title="Готовность тем" />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer p-5 lg:p-10">
          <Link href="/teacher" className="prism-pill">← Учительская</Link>
          <div className="mt-7 grid gap-6 lg:grid-cols-[1fr_620px] lg:items-end">
            <div>
              <div className="prism-kicker">Monitor · Teacher Ops</div>
              <h1 className="prism-title">Матрица <span className="accent">готовности</span></h1>
              <p className="prism-copy">Темы, материалы, источники, fallback и follow-up покрытие — в одном операционном экране.</p>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <Metric label="Темы" value={summary.topics} />
              <Metric label="Материалы" value={summary.materials} />
              <Metric label="Chunks" value={summary.chunks} />
              <Metric label="Fallback" value={summary.fallbacks} />
              <Metric label="Follow-up" value={summary.followups} />
            </div>
          </div>

          <div className="mt-7 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              {PRIORITIES.map((value) => (
                <button key={value || "all"} type="button" onClick={() => setPriority(value)} className={`console-pill ${priority === value ? "console-pill-active" : ""}`}>{value || "Все"}</button>
              ))}
            </div>
            <Link href="/teacher/generate" className="prism-action primary">+ Материал</Link>
          </div>

          {error && <div className="prism-card pad mt-5 text-red-500">{error}</div>}
          {busy && <div className="mt-5 text-[color:var(--prism-muted)]">Загрузка…</div>}

          {!busy && !error && (
            <>
              <div className="mt-5 grid gap-3 lg:hidden">
                {rows.map((row) => <ReadinessCard key={row.topic_id} row={row} />)}
              </div>
              <div className="mt-5 hidden overflow-hidden rounded-[30px] border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/78 shadow-[var(--prism-shadow)] lg:block">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-[color:var(--prism-line)] text-sm">
                    <thead className="bg-[color:var(--prism-panel-solid)]/80 text-left text-xs uppercase tracking-[0.16em] text-[color:var(--prism-muted)]">
                      <tr>{['Тема','Priority','Материалы','Chunks','Fallback','Follow-up','Explain','Practice','Sources','Manual'].map((h) => <th key={h} className="px-4 py-3">{h}</th>)}</tr>
                    </thead>
                    <tbody className="divide-y divide-[color:var(--prism-line)]">
                      {rows.map((row) => (
                        <tr key={row.topic_id} className="hover:bg-[color:var(--prism-panel)]">
                          <td className="max-w-md px-4 py-3"><Link href={`/teacher/topics/${row.topic_id}`} className="font-black text-[color:var(--prism-accent)]">#{row.topic_id} · {row.topic_name}</Link><div className="text-xs text-[color:var(--prism-muted)]">{row.section_name}</div></td>
                          <td className="px-4 py-3"><Pill value={row.priority} /></td>
                          <td className="px-4 py-3 tabular-nums">{row.material_count}</td>
                          <td className="px-4 py-3 tabular-nums">{row.chunk_count}</td>
                          <td className="px-4 py-3 tabular-nums">{row.fallback_count}</td>
                          <td className="px-4 py-3 tabular-nums">{row.followup_count}</td>
                          <td className="px-4 py-3"><Pill value={row.explain_status} /></td>
                          <td className="px-4 py-3"><Pill value={row.practice_status} /></td>
                          <td className="px-4 py-3"><Pill value={row.source_status} /></td>
                          <td className="px-4 py-3"><Pill value={row.manual_qa_status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="prism-card pad"><div className="text-[10px] font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">{label}</div><div className="mt-1 text-2xl font-black">{value}</div></div>;
}

function ReadinessCard({ row }: { row: TopicReadiness }) {
  return (
    <Link href={`/teacher/topics/${row.topic_id}`} className="prism-card prism-topic-card pad block">
      <div className="flex items-start justify-between gap-3">
        <div><div className="text-xs font-black uppercase tracking-[0.16em] text-[color:var(--prism-accent)]">#{row.topic_id} · {row.priority}</div><div className="mt-1 text-lg font-black">{row.topic_name}</div><div className="mt-1 text-xs text-[color:var(--prism-muted)]">{row.section_name}</div></div>
        <Pill value={row.manual_qa_status} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <Small label="Материалы" value={row.material_count} /><Small label="Chunks" value={row.chunk_count} /><Small label="Fallback" value={row.fallback_count} /><Small label="Follow-up" value={row.followup_count} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2"><Pill value={row.explain_status} /><Pill value={row.practice_status} /><Pill value={row.source_status} /></div>
    </Link>
  );
}

function Small({ label, value }: { label: string; value: number }) {
  return <div className="rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/50 p-3"><div className="text-[10px] font-black uppercase tracking-[0.16em] text-[color:var(--prism-muted)]">{label}</div><div className="mt-1 text-lg font-black">{value}</div></div>;
}

function Pill({ value }: { value: string }) {
  const good = ["Smoke OK", "Verified", "OK", "P0"].includes(value);
  const warn = ["TODO", "P1", "P2"].includes(value);
  return <span className={`rounded-full px-2.5 py-1 text-xs font-black ${good ? "bg-emerald-100 text-emerald-800" : warn ? "bg-amber-100 text-amber-800" : "bg-brand-100 text-brand-800"}`}>{value}</span>;
}
