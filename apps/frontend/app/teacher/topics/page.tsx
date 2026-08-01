"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
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

  const summary = useMemo(() => rows.reduce((acc, row) => {
    acc.topics += 1; acc.materials += row.material_count; acc.chunks += row.chunk_count; acc.fallbacks += row.fallback_count; acc.followups += row.followup_count; return acc;
  }, { topics: 0, materials: 0, chunks: 0, fallbacks: 0, followups: 0 }), [rows]);

  return (
    <main className="premium-shell min-h-screen p-4 sm:p-8">
      <section className="premium-container">
        <header className="premium-hero p-6 text-white sm:p-9">
          <Link href="/teacher" className="text-sm font-bold text-white/70 hover:text-white">← Учительская</Link>
          <div className="mt-5 grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
            <div>
              <div className="premium-kicker">Teacher Ops · Readiness</div>
              <h1 className="premium-title mt-4 text-5xl font-black sm:text-7xl">Готовность тем</h1>
              <p className="premium-copy mt-4 max-w-2xl text-lg">Операционная карта MVP: материалы, RAG chunks, fallback и follow-up coverage по каждой теме.</p>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 lg:grid-cols-5">
              <Metric label="Темы" value={summary.topics} />
              <Metric label="Материалы" value={summary.materials} />
              <Metric label="Chunks" value={summary.chunks} />
              <Metric label="Fallback" value={summary.fallbacks} />
              <Metric label="Follow-up" value={summary.followups} />
            </div>
          </div>
        </header>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <div className="premium-chip-row flex flex-wrap gap-2">
            {PRIORITIES.map((value) => (
              <button key={value || "all"} type="button" onClick={() => setPriority(value)} className={priority === value ? "brand-gradient text-white" : ""}>
                {value || "Все"}
              </button>
            ))}
          </div>
          <Link href="/teacher/generate" className="brand-gradient rounded-full px-5 py-3 text-sm font-black text-white shadow-glow">+ Материал</Link>
        </div>

        {error && <div className="lesson-readable mt-4 rounded-2xl p-4 text-sm text-danger">{error}</div>}
        {busy && <div className="mt-4 text-sm text-white/60">Загрузка…</div>}

        {!busy && !error && (
          <>
            <div className="mt-5 grid gap-3 lg:hidden">
              {rows.map((row) => (
                <Link key={row.topic_id} href={`/teacher/topics/${row.topic_id}`} className="lesson-readable block rounded-[24px] p-4 shadow-glow">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-xs font-black uppercase tracking-[0.16em] text-brand-700">#{row.topic_id} · {row.priority}</div>
                      <div className="mt-1 text-lg font-black text-[#171022]">{row.topic_name}</div>
                      <div className="mt-1 text-xs text-[#6b5a80]">{row.section_name}</div>
                    </div>
                    <Pill value={row.manual_qa_status} />
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-[#4a3d5d]">
                    <MobileStat label="Материалы" value={row.material_count} />
                    <MobileStat label="Chunks" value={row.chunk_count} />
                    <MobileStat label="Fallback" value={row.fallback_count} />
                    <MobileStat label="Follow-up" value={row.followup_count} />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Pill value={row.explain_status} />
                    <Pill value={row.practice_status} />
                    <Pill value={row.source_status} />
                  </div>
                </Link>
              ))}
            </div>

            <div className="mt-5 hidden overflow-hidden rounded-[30px] border border-white/12 bg-white/92 shadow-glow lg:block">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-brand-200/60 text-sm text-[#171022]">
                  <thead className="bg-[#2b1248] text-left text-xs uppercase tracking-[0.16em] text-white/75">
                    <tr>
                      {['Тема','Priority','Материалы','Chunks','Fallback','Follow-up','Explain','Practice','Sources','Manual'].map((h) => <th key={h} className="px-4 py-3">{h}</th>)}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-brand-100/80">
                    {rows.map((row) => (
                      <tr key={row.topic_id} className="transition-colors hover:bg-brand-50">
                        <td className="max-w-md px-4 py-3">
                          <Link href={`/teacher/topics/${row.topic_id}`} className="font-black text-brand-700 hover:underline">#{row.topic_id} · {row.topic_name}</Link>
                          <div className="text-xs text-[#6b5a80]">{row.section_name}</div>
                        </td>
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
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-2xl border border-white/12 bg-white/8 p-3 text-white"><div className="text-[10px] uppercase tracking-[0.18em] text-white/45">{label}</div><div className="mt-1 text-2xl font-black">{value}</div></div>;
}

function MobileStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-brand-100 bg-white/70 p-3">
      <div className="text-[10px] font-black uppercase tracking-[0.16em] text-[#7b6c91]">{label}</div>
      <div className="mt-1 text-lg font-black text-[#171022]">{value}</div>
    </div>
  );
}

function Pill({ value }: { value: string }) {
  const good = ["Smoke OK", "Verified", "OK", "P0"].includes(value);
  const warn = ["TODO", "P1", "P2"].includes(value);
  return <span className={`rounded-full px-2.5 py-1 text-xs font-black ${good ? "bg-emerald-100 text-emerald-800" : warn ? "bg-amber-100 text-amber-800" : "bg-brand-100 text-brand-800"}`}>{value}</span>;
}
