"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Header from "@/components/Header";
import type { RagRebuildJob, Topic, TopicFollowup, TopicPracticeFallback, User } from "@/types";


function safeJsonArray<T>(value: string): T[] {
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed as T[] : [];
  } catch {
    return [];
  }
}

function topicCompleteness(followupsText: string, fallbacksText: string) {
  const followups = safeJsonArray<TopicFollowup>(followupsText);
  const fallbacks = safeJsonArray<TopicPracticeFallback>(fallbacksText);
  const activeFallbacks = fallbacks.filter((item) => item.is_active !== false && item.question_text && item.correct_answer);
  const checks = [
    { label: "Follow-up кнопки", ok: followups.length >= 3, note: `${followups.length}/3+` },
    { label: "Fallback-задания", ok: activeFallbacks.length >= 1, note: `${activeFallbacks.length}/1+` },
    { label: "Пояснение ответа", ok: activeFallbacks.every((item) => Boolean(item.explanation)), note: "у активных задач" },
    { label: "Типичные ошибки", ok: activeFallbacks.some((item) => (item.typical_mistakes || []).length > 0), note: "минимум у одной задачи" },
  ];
  return { checks, ready: checks.every((item) => item.ok) };
}

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

  const followups = safeJsonArray<TopicFollowup>(followupsText);
  const fallbacks = safeJsonArray<TopicPracticeFallback>(fallbacksText);

  function updateFollowup(index: number, patch: Partial<TopicFollowup>) {
    const next = [...followups];
    next[index] = { ...next[index], ...patch };
    setFollowupsText(JSON.stringify(next, null, 2));
  }

  function addFollowup() {
    const next = [
      ...followups,
      { label: "Новая кнопка", prompt: "Сформулируй следующий вопрос по теме", kind: "choice", order_index: followups.length + 1 },
    ];
    setFollowupsText(JSON.stringify(next, null, 2));
  }

  function removeFollowup(index: number) {
    setFollowupsText(JSON.stringify(followups.filter((_, idx) => idx !== index), null, 2));
  }

  function updateFallback(index: number, patch: Partial<TopicPracticeFallback>) {
    const next = [...fallbacks];
    next[index] = { ...next[index], ...patch };
    setFallbacksText(JSON.stringify(next, null, 2));
  }

  function addFallback() {
    const next = [...fallbacks, { ...DEFAULT_FALLBACK, order_index: fallbacks.length + 1 }];
    setFallbacksText(JSON.stringify(next, null, 2));
  }

  function removeFallback(index: number) {
    setFallbacksText(JSON.stringify(fallbacks.filter((_, idx) => idx !== index), null, 2));
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

  const completeness = topicCompleteness(followupsText, fallbacksText);

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
    <main className="prism-shell teacher-console teacher-topic-editor min-h-dvh">
      <Header user={user} backHref="/teacher/topics" title={`Тема #${topicId}`} />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer p-5 lg:p-10">
      <section className="border-b border-[color:var(--prism-line)] pb-5">
        <Link href="/teacher/topics" className="prism-action w-fit px-4 py-2 text-sm">← Готовность тем</Link>
        <h1 className="mt-1 text-2xl font-bold">Тема #{topicId}{topic ? ` · ${topic.name}` : ""}</h1>
        <p className="mt-1 text-sm text-[color:var(--prism-muted)]">Stage 4 MVP: followups, fallback-задания, status и safe RAG job.</p>
      </section>

      {error && <div className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</div>}
      {message && <div className="mt-4 rounded-2xl border border-emerald-300/30 bg-emerald-400/10 p-3 text-sm text-[color:var(--prism-green)]">{message}</div>}
      {busy && <div className="mt-4 text-sm text-[color:var(--prism-muted)]">Загрузка…</div>}


      <section className="mt-4 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-4 shadow-glow">
        <div className="prism-kicker">Готовность публикации</div>
        <h2 className="mt-1 text-lg font-semibold">{completeness.ready ? "Тема выглядит готовой" : "Нужно закрыть пробелы"}</h2>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {completeness.checks.map((check) => (
            <div key={check.label} className="rounded-2xl border border-[color:var(--prism-line)] bg-black/10 p-3 text-sm">
              <div className={check.ok ? "text-[color:var(--prism-green)]" : "text-amber-200"}>{check.ok ? "✓" : "•"} {check.label}</div>
              <div className="mt-1 text-xs text-[color:var(--prism-muted)]">{check.note}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-4 grid gap-4 lg:grid-cols-2">
        <FollowupsEditor
          value={followups}
          rawValue={followupsText}
          disabled={busy}
          onChange={updateFollowup}
          onAdd={addFollowup}
          onRemove={removeFollowup}
          onRawChange={setFollowupsText}
          onSave={saveFollowups}
        />
        <FallbacksEditor
          value={fallbacks}
          rawValue={fallbacksText}
          disabled={busy}
          onChange={updateFallback}
          onAdd={addFallback}
          onRemove={removeFallback}
          onRawChange={setFallbacksText}
          onSave={saveFallbacks}
        />
      </section>

      <section className="mt-4 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-4 shadow-glow">
        <h2 className="text-lg font-semibold">Manual QA статус</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <label className="text-sm">
            Статус
            <select value={manualQaStatus} onChange={(e) => setManualQaStatus(e.target.value)} className="mt-1 block w-full prism-input">
              <option value="todo">todo</option>
              <option value="ok">ok</option>
              <option value="issue">issue</option>
              <option value="blocked">blocked</option>
            </select>
          </label>
          <label className="md:col-span-2 text-sm">
            Notes
            <input value={notes} onChange={(e) => setNotes(e.target.value)} className="mt-1 block w-full prism-input" />
          </label>
        </div>
        <button onClick={saveStatus} disabled={busy} className="mt-3 prism-action primary px-4 py-2 text-sm disabled:opacity-50">Сохранить статус</button>
      </section>

      <section className="mt-4 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-4 shadow-glow">
        <h2 className="text-lg font-semibold">RAG rebuild</h2>
        <p className="mt-1 text-sm text-[color:var(--prism-muted)]">MVP safe mode: dry-run verification, без удаления chunks.</p>
        <button onClick={rebuildRag} disabled={busy} className="mt-3 prism-action hover-warn px-4 py-2 text-sm disabled:opacity-50">Запустить safe rebuild</button>
        {job && <pre className="mt-3 overflow-auto rounded-2xl border border-[color:var(--prism-line)] bg-black/20 p-3 text-xs text-[color:var(--prism-ink)]">{JSON.stringify(job, null, 2)}</pre>}
      </section>
        </div>
        </div>
      </section>
    </main>
  );
}

function FollowupsEditor({
  value,
  rawValue,
  disabled,
  onChange,
  onAdd,
  onRemove,
  onRawChange,
  onSave,
}: {
  value: TopicFollowup[];
  rawValue: string;
  disabled: boolean;
  onChange: (index: number, patch: Partial<TopicFollowup>) => void;
  onAdd: () => void;
  onRemove: (index: number) => void;
  onRawChange: (value: string) => void;
  onSave: () => void;
}) {
  return (
    <section className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-4 shadow-glow">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Follow-up кнопки</h2>
        <button type="button" onClick={onAdd} disabled={disabled} className="prism-action px-4 py-2 text-sm">Добавить</button>
      </div>
      <div className="mt-4 grid gap-3">
        {value.length === 0 && <p className="text-sm text-[color:var(--prism-muted)]">Кнопок пока нет.</p>}
        {value.map((item, index) => (
          <div key={index} className="rounded-3xl border border-[color:var(--prism-line)] bg-black/10 p-3">
            <div className="grid gap-2 md:grid-cols-[0.8fr_1.2fr]">
              <label className="text-xs text-[color:var(--prism-muted)]">Label
                <input value={item.label} onChange={(event) => onChange(index, { label: event.target.value })} className="prism-input mt-1 w-full text-sm" />
              </label>
              <label className="text-xs text-[color:var(--prism-muted)]">Prompt
                <input value={item.prompt} onChange={(event) => onChange(index, { prompt: event.target.value })} className="prism-input mt-1 w-full text-sm" />
              </label>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <select value={item.kind} onChange={(event) => onChange(index, { kind: event.target.value })} className="prism-input w-fit text-sm">
                <option value="choice">choice</option>
                <option value="next">next</option>
                <option value="review">review</option>
              </select>
              <button type="button" onClick={() => onRemove(index)} disabled={disabled} className="prism-action hover-danger px-3 py-2 text-xs">Удалить</button>
            </div>
          </div>
        ))}
      </div>
      <button onClick={onSave} disabled={disabled} className="mt-3 prism-action primary px-4 py-2 text-sm disabled:opacity-50">Сохранить followups</button>
      <details className="mt-4 rounded-2xl border border-[color:var(--prism-line)] bg-black/10 p-3">
        <summary className="cursor-pointer text-xs font-black uppercase tracking-wide text-[color:var(--prism-muted)]">Raw JSON fallback</summary>
        <textarea value={rawValue} onChange={(event) => onRawChange(event.target.value)} rows={10} className="prism-input mt-3 w-full resize-y p-3 font-mono text-xs" />
      </details>
    </section>
  );
}

function FallbacksEditor({
  value,
  rawValue,
  disabled,
  onChange,
  onAdd,
  onRemove,
  onRawChange,
  onSave,
}: {
  value: TopicPracticeFallback[];
  rawValue: string;
  disabled: boolean;
  onChange: (index: number, patch: Partial<TopicPracticeFallback>) => void;
  onAdd: () => void;
  onRemove: (index: number) => void;
  onRawChange: (value: string) => void;
  onSave: () => void;
}) {
  return (
    <section className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-4 shadow-glow">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Fallback-задания</h2>
        <button type="button" onClick={onAdd} disabled={disabled} className="prism-action px-4 py-2 text-sm">Добавить</button>
      </div>
      <div className="mt-4 grid gap-3">
        {value.map((item, index) => (
          <div key={index} className="rounded-3xl border border-[color:var(--prism-line)] bg-black/10 p-3">
            <label className="text-xs text-[color:var(--prism-muted)]">Вопрос
              <textarea value={item.question_text} onChange={(event) => onChange(index, { question_text: event.target.value })} rows={3} className="prism-input mt-1 w-full resize-y p-3 text-sm" />
            </label>
            <div className="mt-2 grid gap-2 md:grid-cols-2">
              <label className="text-xs text-[color:var(--prism-muted)]">Правильный ответ
                <input value={item.correct_answer} onChange={(event) => onChange(index, { correct_answer: event.target.value })} className="prism-input mt-1 w-full text-sm" />
              </label>
              <label className="text-xs text-[color:var(--prism-muted)]">Тип
                <select value={item.type} onChange={(event) => onChange(index, { type: event.target.value })} className="prism-input mt-1 w-full text-sm">
                  <option value="single">single</option>
                  <option value="numeric">numeric</option>
                  <option value="text">text</option>
                </select>
              </label>
            </div>
            <label className="mt-2 block text-xs text-[color:var(--prism-muted)]">Варианты ответа, через `|`
              <input value={(item.options || []).join(" | ")} onChange={(event) => onChange(index, { options: event.target.value.split("|").map((x) => x.trim()).filter(Boolean) })} className="prism-input mt-1 w-full text-sm" />
            </label>
            <label className="mt-2 block text-xs text-[color:var(--prism-muted)]">Объяснение
              <textarea value={item.explanation} onChange={(event) => onChange(index, { explanation: event.target.value })} rows={3} className="prism-input mt-1 w-full resize-y p-3 text-sm" />
            </label>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <label className="prism-toggle-pill min-h-0 px-3 py-2 text-xs"><input type="checkbox" checked={item.is_active !== false} onChange={(event) => onChange(index, { is_active: event.target.checked })} className="sr-only" /><span aria-hidden="true" className="prism-toggle-dot" /><span>active</span></label>
              <button type="button" onClick={() => onRemove(index)} disabled={disabled} className="prism-action hover-danger px-3 py-2 text-xs">Удалить</button>
            </div>
          </div>
        ))}
      </div>
      <button onClick={onSave} disabled={disabled} className="mt-3 prism-action primary px-4 py-2 text-sm disabled:opacity-50">Сохранить задания</button>
      <details className="mt-4 rounded-2xl border border-[color:var(--prism-line)] bg-black/10 p-3">
        <summary className="cursor-pointer text-xs font-black uppercase tracking-wide text-[color:var(--prism-muted)]">Raw JSON fallback</summary>
        <textarea value={rawValue} onChange={(event) => onRawChange(event.target.value)} rows={14} className="prism-input mt-3 w-full resize-y p-3 font-mono text-xs" />
      </details>
    </section>
  );
}
