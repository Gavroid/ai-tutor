"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { RagRebuildJob, Topic, TopicFollowup, TopicPracticeFallback, User } from "@/types";

const DEFAULT_FALLBACK: TopicPracticeFallback = {
  question_text: "",
  type: "single",
  options: ["", ""],
  correct_answer: "",
  explanation: "",
  typical_mistakes: [],
  difficulty: 1,
  order_index: 1,
  is_active: true,
};

export default function TeacherTopicDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const topicId = Number(params?.id);
  const [user, setUser] = useState<User | null>(null);
  const [topic, setTopic] = useState<Topic | null>(null);
  const [followupsText, setFollowupsText] = useState("[]");
  const [fallbacksText, setFallbacksText] = useState("[]");
  const [manualQaStatus, setManualQaStatus] = useState("todo");
  const [notes, setNotes] = useState("");
  const [job, setJob] = useState<RagRebuildJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.me().then(setUser).catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!user || !topicId || Number.isNaN(topicId)) return;
    let cancelled = false;
    setBusy(true);
    setError(null);
    Promise.all([
      api.topic(topicId),
      api.teacherGetFollowups(topicId),
      api.teacherGetFallbacks(topicId),
    ])
      .then(([loadedTopic, followups, fallbacks]) => {
        if (cancelled) return;
        setTopic(loadedTopic);
        setFollowupsText(JSON.stringify(followups, null, 2));
        setFallbacksText(JSON.stringify(fallbacks.length ? fallbacks : [DEFAULT_FALLBACK], null, 2));
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Ошибка загрузки темы"))
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [user, topicId]);

  function parseFollowups(): TopicFollowup[] {
    const parsed = JSON.parse(followupsText);
    if (!Array.isArray(parsed)) throw new Error("Followups должны быть JSON-массивом");
    return parsed as TopicFollowup[];
  }

  function parseFallbacks(): TopicPracticeFallback[] {
    const parsed = JSON.parse(fallbacksText);
    if (!Array.isArray(parsed)) throw new Error("Fallbacks должны быть JSON-массивом");
    return parsed as TopicPracticeFallback[];
  }

  async function saveFollowups() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const saved = await api.teacherPutFollowups(topicId, parseFollowups());
      setFollowupsText(JSON.stringify(saved, null, 2));
      setMessage("Follow-up кнопки сохранены");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ошибка сохранения followups");
    } finally {
      setBusy(false);
    }
  }

  async function saveFallbacks() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const saved = await api.teacherPutFallbacks(topicId, parseFallbacks());
      setFallbacksText(JSON.stringify(saved, null, 2));
      setMessage("Fallback-задания сохранены");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ошибка сохранения fallbacks");
    } finally {
      setBusy(false);
    }
  }

  async function saveStatus() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.teacherPatchTopicStatus(topicId, { manual_qa_status: manualQaStatus, notes });
      setMessage("Статус темы сохранён");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ошибка сохранения статуса");
    } finally {
      setBusy(false);
    }
  }

  async function rebuildRag() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.teacherRebuildTopicRag(topicId);
      setJob(result);
      setMessage("RAG job создан");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ошибка RAG rebuild");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="border-b border-slate-200 pb-3">
        <Link href="/teacher/topics" className="text-sm text-sky-600 hover:underline">← Готовность тем</Link>
        <h1 className="mt-1 text-2xl font-bold">Тема #{topicId}{topic ? ` · ${topic.name}` : ""}</h1>
        <p className="mt-1 text-sm text-slate-600">Stage 4 MVP: followups, fallback-задания, status и safe RAG job.</p>
      </header>

      {error && <div className="mt-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
      {message && <div className="mt-4 rounded-md bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
      {busy && <div className="mt-4 text-sm text-slate-500">Загрузка…</div>}

      <section className="mt-4 grid gap-4 lg:grid-cols-2">
        <EditorCard title="Follow-up кнопки" value={followupsText} onChange={setFollowupsText} onSave={saveFollowups} disabled={busy} />
        <EditorCard title="Fallback-задания" value={fallbacksText} onChange={setFallbacksText} onSave={saveFallbacks} disabled={busy} rows={18} />
      </section>

      <section className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold">Manual QA статус</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <label className="text-sm">
            Статус
            <select value={manualQaStatus} onChange={(e) => setManualQaStatus(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2">
              <option value="todo">todo</option>
              <option value="ok">ok</option>
              <option value="issue">issue</option>
              <option value="blocked">blocked</option>
            </select>
          </label>
          <label className="md:col-span-2 text-sm">
            Notes
            <input value={notes} onChange={(e) => setNotes(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
        </div>
        <button onClick={saveStatus} disabled={busy} className="mt-3 rounded-md bg-sky-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Сохранить статус</button>
      </section>

      <section className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold">RAG rebuild</h2>
        <p className="mt-1 text-sm text-slate-600">MVP safe mode: dry-run verification, без удаления chunks.</p>
        <button onClick={rebuildRag} disabled={busy} className="mt-3 rounded-md bg-amber-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Запустить safe rebuild</button>
        {job && <pre className="mt-3 overflow-auto rounded-md bg-slate-100 p-3 text-xs">{JSON.stringify(job, null, 2)}</pre>}
      </section>
    </main>
  );
}

function EditorCard({ title, value, onChange, onSave, disabled, rows = 12 }: { title: string; value: string; onChange: (value: string) => void; onSave: () => void; disabled: boolean; rows?: number }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold">{title}</h2>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={rows} className="mt-3 w-full rounded-md border border-slate-300 p-3 font-mono text-xs" />
      <button onClick={onSave} disabled={disabled} className="mt-3 rounded-md bg-sky-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Сохранить</button>
    </section>
  );
}
