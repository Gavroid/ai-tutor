"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, getToken, setToken } from "@/lib/api";
import type { MaterialDraftOut, Subject, Topic, User } from "@/types";

type SourceType = "text" | "file" | "topic";

interface TopicOption extends Topic {
  subject_name: string;
}

export default function TeacherGeneratePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [topics, setTopics] = useState<TopicOption[]>([]);
  const [topicId, setTopicId] = useState<number | null>(null);
  const [sourceType, setSourceType] = useState<SourceType>("topic");
  const [text, setText] = useState("");
  const [hint, setHint] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<"input" | "preview">("input");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MaterialDraftOut | null>(null);

  useEffect(() => {
    // Sprint 27: cookie-based auth. /me 401 → /login.
    api.me().then(setUser).catch(() => {
      router.push("/login");
    });
  }, [router]);

  useEffect(() => {
    if (!user) return;
    loadTopics();
  }, [user]);

  async function loadTopics() {
    try {
      const subjects = await api.subjects();
      const all: TopicOption[] = [];
      for (const s of subjects) {
        const topics = await api.subjectTopics(s.id);
        for (const t of topics) {
          all.push({ ...t, subject_name: s.name });
        }
      }
      setTopics(all);
    } catch (e) {
      setError("Не удалось загрузить список тем");
    }
  }

  async function handleGenerate() {
    if (!topicId) {
      setError("Выберите тему");
      return;
    }
    if (sourceType === "text" && !text.trim()) {
      setError("Введите текст источника");
      return;
    }
    if (sourceType === "file" && !file) {
      setError("Выберите файл");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      let filePath: string | undefined;
      if (sourceType === "file" && file) {
        const uploaded = await api.teacherUploadSource(file);
        filePath = uploaded.file_path;
      }
      const data = await api.teacherGenerateMaterial({
        topic_id: topicId,
        source_type: sourceType,
        text: sourceType === "text" ? text : undefined,
        file_path: filePath,
        topic_hint: hint || undefined,
      });
      setResult(data);
      setStep("preview");
    } catch (e: any) {
      setError(e?.body?.detail || "Ошибка генерации");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-6">
      <header className="border-b border-slate-200 pb-3">
        <Link href="/teacher" className="text-sm text-sky-600 hover:underline">
          ← К списку материалов
        </Link>
        <h1 className="mt-1 text-2xl font-bold">Генерация материала</h1>
        <p className="mt-1 text-sm text-slate-600">
          Выберите тему и источник. AI создаст черновик по единому шаблону —
          конспект, задачи, тест и карточки для повторения.
        </p>
      </header>

      {/* Step indicator */}
      <ol className="mt-4 flex items-center gap-2 text-sm">
        <Step n={1} active={step === "input"} done={step === "preview"}>
          Источник
        </Step>
        <span className="text-slate-300">→</span>
        <Step n={2} active={step === "preview"}>
          Проверка
        </Step>
      </ol>

      {error && (
        <div className="mt-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {step === "input" && (
        <section className="mt-4 space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          {/* Topic */}
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Тема (из 7 класса)
            </label>
            <select
              value={topicId ?? ""}
              onChange={(e) => setTopicId(Number(e.target.value) || null)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">— выберите тему —</option>
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.subject_name} → {t.name}
                </option>
              ))}
            </select>
          </div>

          {/* Source type */}
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Источник
            </label>
            <div className="mt-2 grid gap-2 md:grid-cols-3">
              <SourceTypeRadio
                current={sourceType}
                value="topic"
                onChange={setSourceType}
                label="Только тема"
                hint="AI сгенерирует по названию и описанию"
              />
              <SourceTypeRadio
                current={sourceType}
                value="text"
                onChange={setSourceType}
                label="Текст"
                hint="Вставить параграф или конспект"
              />
              <SourceTypeRadio
                current={sourceType}
                value="file"
                onChange={setSourceType}
                label="Файл"
                hint="PDF / DOCX / TXT"
              />
            </div>
          </div>

          {/* Source content */}
          {sourceType === "text" && (
            <div>
              <label className="block text-sm font-medium text-slate-700">
                Текст источника
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={10}
                placeholder="Вставьте параграф из учебника или свой конспект..."
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-xs"
              />
              <p className="mt-1 text-xs text-slate-500">
                Максимум 20 000 символов
              </p>
            </div>
          )}

          {sourceType === "file" && (
            <div>
              <label className="block text-sm font-medium text-slate-700">
                Файл
              </label>
              <input
                type="file"
                accept=".pdf,.docx,.txt,.md"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="mt-1 block w-full text-sm"
              />
              <p className="mt-1 text-xs text-slate-500">
                PDF / DOCX / TXT. До 20 МБ.
              </p>
            </div>
          )}

          {/* Hint */}
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Доп. указание (необязательно)
            </label>
            <input
              type="text"
              value={hint}
              onChange={(e) => setHint(e.target.value)}
              placeholder="Например: «сделай акцент на практических задачах»"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>

          <div className="flex justify-end gap-3">
            <Link
              href="/teacher"
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Отмена
            </Link>
            <button
              onClick={handleGenerate}
              disabled={busy || !topicId}
              className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50"
            >
              {busy ? "Генерация…" : "Сгенерировать"}
            </button>
          </div>
        </section>
      )}

      {step === "preview" && result && (
        <PreviewStep
          material={result}
          onClose={() => router.push(`/teacher/materials/${result.id}`)}
        />
      )}
    </main>
  );
}

function Step({
  n,
  active,
  done,
  children,
}: {
  n: number;
  active: boolean;
  done?: boolean;
  children: React.ReactNode;
}) {
  return (
    <li
      className={`flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${
        active
          ? "bg-sky-600 text-white"
          : done
            ? "bg-emerald-100 text-emerald-800"
            : "bg-slate-100 text-slate-500"
      }`}
    >
      <span>{n}.</span>
      <span>{children}</span>
    </li>
  );
}

function SourceTypeRadio({
  current,
  value,
  onChange,
  label,
  hint,
}: {
  current: SourceType;
  value: SourceType;
  onChange: (v: SourceType) => void;
  label: string;
  hint: string;
}) {
  const active = current === value;
  return (
    <button
      type="button"
      onClick={() => onChange(value)}
      className={`rounded-lg border p-3 text-left transition ${
        active
          ? "border-sky-500 bg-sky-50"
          : "border-slate-200 bg-white hover:border-slate-300"
      }`}
    >
      <div className="text-sm font-medium">{label}</div>
      <div className="text-xs text-slate-500">{hint}</div>
    </button>
  );
}

function PreviewStep({
  material,
  onClose,
}: {
  material: MaterialDraftOut;
  onClose: () => void;
}) {
  const c = material.content;
  return (
    <section className="mt-4 space-y-6 rounded-xl border border-emerald-200 bg-emerald-50/50 p-6 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <span className="rounded bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-800">
            ✓ Черновик создан
          </span>
          <h2 className="mt-2 text-xl font-bold">{c.title}</h2>
          <p className="text-sm text-slate-600">{c.purpose}</p>
        </div>
        <button
          onClick={onClose}
          className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
        >
          Открыть и одобрить →
        </button>
      </div>

      {c.ai_uncertainty_notes.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
          <strong className="text-amber-900">⚠ Что AI не уверен:</strong>
          <ul className="mt-1 list-disc pl-5 text-xs text-amber-800">
            {c.ai_uncertainty_notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-lg bg-white p-4 text-sm">
        <h3 className="font-semibold">📚 Главных мыслей: {c.key_ideas.length}</h3>
        <h3 className="mt-2 font-semibold">✏️ Практических задач: {c.practice_tasks.length}</h3>
        <h3 className="mt-2 font-semibold">📝 Вопросов теста: {c.mini_test.length}</h3>
        <h3 className="mt-2 font-semibold">🎴 Карточек: {c.flashcards.length}</h3>
      </div>
    </section>
  );
}
