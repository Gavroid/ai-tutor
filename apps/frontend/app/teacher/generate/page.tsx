"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Header from "@/components/Header";
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
    <main className="prism-shell teacher-console teacher-generate-console min-h-dvh"><Header user={user} backHref="/teacher" title="Генерация материала" /><section className="py-3 sm:py-5"><div className="prism-frame"><div className="prism-layer mx-auto max-w-5xl p-5 lg:p-10">
      <section className="border-b border-[color:var(--prism-line)] pb-4">
        <Link href="/teacher" className="prism-action w-fit px-4 py-2 text-sm">
          ← К списку материалов
        </Link>
        <h1 className="mt-4 text-2xl font-bold text-[color:var(--prism-ink)]">Генерация материала</h1>
        <p className="mt-1 text-sm text-[color:var(--prism-muted)]">
          Выберите тему и источник. AI создаст черновик по единому шаблону —
          конспект, задачи, тест и карточки для повторения.
        </p>
      </section>

      {/* Step indicator */}
      <ol className="mt-4 flex items-center gap-2 text-sm">
        <Step n={1} active={step === "input"} done={step === "preview"}>
          Источник
        </Step>
        <span className="text-[color:var(--prism-muted)]">→</span>
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
        <section className="mt-4 space-y-4 rounded-xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-6 shadow-glow">
          {/* Topic */}
          <div>
            <label className="block text-sm font-medium text-[color:var(--prism-muted)]">
              Тема (из 7 класса)
            </label>
            <select
              value={topicId ?? ""}
              onChange={(e) => setTopicId(Number(e.target.value) || null)}
              className="mt-1 w-full rounded-md prism-input text-sm"
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
            <label className="block text-sm font-medium text-[color:var(--prism-muted)]">
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
              <label className="block text-sm font-medium text-[color:var(--prism-muted)]">
                Текст источника
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={10}
                placeholder="Вставьте параграф из учебника или свой конспект..."
                className="mt-1 w-full rounded-md prism-input font-mono text-xs"
              />
              <p className="mt-1 text-xs text-[color:var(--prism-muted)]">
                Максимум 20 000 символов
              </p>
            </div>
          )}

          {sourceType === "file" && (
            <div>
              <label className="block text-sm font-medium text-[color:var(--prism-muted)]">
                Файл
              </label>
              <label className="mt-2 flex cursor-pointer flex-col gap-3 rounded-3xl border border-[color:var(--prism-line)] bg-black/10 p-4 transition hover:border-[color:var(--prism-accent)] sm:flex-row sm:items-center sm:justify-between">
                <span className="min-w-0">
                  <span className="block text-sm font-black text-[color:var(--prism-ink)]">
                    {file ? file.name : "Файл не выбран"}
                  </span>
                  <span className="mt-1 block text-xs text-[color:var(--prism-muted)]">
                    PDF / DOCX / TXT · до 20 МБ
                  </span>
                </span>
                <span className="prism-action min-h-0 shrink-0 px-4 py-2 text-sm">Выбрать файл</span>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt,.md"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="sr-only"
                />
              </label>
            </div>
          )}

          {/* Hint */}
          <div>
            <label className="block text-sm font-medium text-[color:var(--prism-muted)]">
              Доп. указание (необязательно)
            </label>
            <input
              type="text"
              value={hint}
              onChange={(e) => setHint(e.target.value)}
              placeholder="Например: «сделай акцент на практических задачах»"
              className="mt-1 w-full rounded-md prism-input text-sm"
            />
          </div>

          <div className="flex justify-end gap-3">
            <Link
              href="/teacher"
              className="prism-action px-4 py-2 text-sm"
            >
              Отмена
            </Link>
            <button
              onClick={handleGenerate}
              disabled={busy || !topicId}
              className="prism-action primary px-4 py-2 text-sm disabled:opacity-50"
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
    </div></div></section></main>
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
          ? "border border-[color:var(--prism-accent)] bg-[color:var(--prism-accent)]/20 text-white"
          : done
            ? "border border-[color:var(--prism-line)] bg-black/10 text-[color:var(--prism-green)]"
            : "border border-[color:var(--prism-line)] bg-black/10 text-[color:var(--prism-muted)]"
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
      className={`rounded-2xl border p-3 text-left transition ${
        active
          ? "border-[color:var(--prism-accent)] bg-[color:var(--prism-panel-solid)]/65 shadow-glow"
          : "border-[color:var(--prism-line)] bg-black/10 hover:border-[color:var(--prism-accent)]"
      }`}
    >
      <div className="text-sm font-black text-[color:var(--prism-ink)]">{label}</div>
      <div className="text-xs text-[color:var(--prism-muted)]">{hint}</div>
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
    <section className="mt-4 space-y-6 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-6 shadow-glow">
      <div className="flex items-start justify-between">
        <div>
          <span className="rounded-full border border-[color:var(--prism-line)] bg-black/10 px-2 py-1 text-xs font-medium text-[color:var(--prism-green)]">
            ✓ Черновик создан
          </span>
          <h2 className="mt-2 text-xl font-bold">{c.title}</h2>
          <p className="text-sm text-[color:var(--prism-muted)]">{c.purpose}</p>
        </div>
        <button
          onClick={onClose}
          className="prism-action primary px-4 py-2 text-sm"
        >
          Открыть и одобрить →
        </button>
      </div>

      {c.ai_uncertainty_notes.length > 0 && (
        <div className="rounded-2xl border border-amber-300/30 bg-amber-400/10 p-3 text-sm">
          <strong className="text-amber-200">⚠ Что AI не уверен:</strong>
          <ul className="mt-1 list-disc pl-5 text-xs text-amber-200">
            {c.ai_uncertainty_notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-2xl border border-[color:var(--prism-line)] bg-black/10 p-4 text-sm text-[color:var(--prism-ink)]">
        <h3 className="font-semibold">📚 Главных мыслей: {c.key_ideas.length}</h3>
        <h3 className="mt-2 font-semibold">✏️ Практических задач: {c.practice_tasks.length}</h3>
        <h3 className="mt-2 font-semibold">📝 Вопросов теста: {c.mini_test.length}</h3>
        <h3 className="mt-2 font-semibold">🎴 Карточек: {c.flashcards.length}</h3>
      </div>
    </section>
  );
}
