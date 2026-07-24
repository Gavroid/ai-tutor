"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api, getToken, setToken } from "@/lib/api";
import type { MaterialDraftOut, MaterialStatus, User } from "@/types";

const STATUS_LABEL: Record<MaterialStatus, string> = {
  draft: "Черновик",
  ai_generated: "AI сгенерировал (требует проверки)",
  teacher_approved: "Одобрено",
  published: "Опубликовано",
};

const STATUS_COLOR: Record<MaterialStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  ai_generated: "bg-amber-100 text-amber-800",
  teacher_approved: "bg-sky-100 text-sky-800",
  published: "bg-emerald-100 text-emerald-800",
};

export default function TeacherMaterialDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = Number(params.id);
  const [user, setUser] = useState<User | null>(null);
  const [material, setMaterial] = useState<MaterialDraftOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Sprint 27: cookie-based auth. /me 401 → /login.
    api.me().then(setUser).catch(() => {
      router.push("/login");
    });
  }, [router]);

  useEffect(() => {
    if (!user || !id) return;
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, id]);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      const data = await api.teacherGetMaterial(id);
      setMaterial(data);
    } catch (e: any) {
      setError(e?.body?.detail || "Ошибка загрузки");
    } finally {
      setBusy(false);
    }
  }

  async function call(fn: () => Promise<MaterialDraftOut>) {
    setBusy(true);
    setError(null);
    try {
      const updated = await fn();
      setMaterial(updated);
    } catch (e: any) {
      setError(e?.body?.detail || "Ошибка");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!material) return;
    if (!confirm(`Удалить материал «${material.title}»? Действие необратимо.`))
      return;
    setBusy(true);
    setError(null);
    try {
      await api.teacherDeleteMaterial(material.id);
      router.push("/teacher");
    } catch (e: any) {
      setError(e?.body?.detail || "Ошибка удаления");
      setBusy(false);
    }
  }

  if (!user || busy || !material) {
    return (
      <main className="mx-auto max-w-4xl p-6">
        {error && (
          <div className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">
            {error}
          </div>
        )}
        <div className="mt-4 text-sm text-slate-500">Загрузка…</div>
      </main>
    );
  }

  const c = material.content;
  const canApprove =
    material.status === "ai_generated" || material.status === "draft";
  const canPublish = material.status === "teacher_approved";
  const canUnpublish = material.status === "published";
  const canDelete =
    material.status !== "published" && material.status !== "teacher_approved";

  return (
    <main className="mx-auto max-w-4xl p-6">
      <header className="border-b border-slate-200 pb-3">
        <Link href="/teacher" className="text-sm text-sky-600 hover:underline">
          ← К списку материалов
        </Link>
        <div className="mt-1 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">{c.title}</h1>
            <div className="mt-1 flex items-center gap-2 text-sm text-slate-600">
              <span
                className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[material.status]}`}
              >
                {STATUS_LABEL[material.status]}
              </span>
              <span>· Тема #{material.topic_id}</span>
              <span>· Источник: {material.source_type}</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {canApprove && (
              <button
                onClick={() => call(() => api.teacherApprove(material.id))}
                disabled={busy}
                className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50"
              >
                ✓ Одобрить
              </button>
            )}
            {canPublish && (
              <button
                onClick={() => call(() => api.teacherPublish(material.id))}
                disabled={busy}
                className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                🚀 Опубликовать
              </button>
            )}
            {canUnpublish && (
              <button
                onClick={() => call(() => api.teacherUnpublish(material.id))}
                disabled={busy}
                className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
              >
                ⏸ Снять с публикации
              </button>
            )}
            {canDelete && (
              <button
                onClick={handleDelete}
                disabled={busy}
                className="rounded-md bg-rose-100 px-4 py-2 text-sm font-medium text-rose-800 hover:bg-rose-200 disabled:opacity-50"
              >
                Удалить
              </button>
            )}
          </div>
        </div>
      </header>

      <section className="mt-4 space-y-6">
        {/* Зачем */}
        <Block title="Зачем эта тема">{c.purpose}</Block>
        {c.connection_to_prior && (
          <Block title="Связь с пройденным">{c.connection_to_prior}</Block>
        )}

        {/* Главные мысли */}
        {c.key_ideas.length > 0 && (
          <Block title={`Главные мысли (${c.key_ideas.length})`}>
            <ol className="list-decimal space-y-2 pl-5">
              {c.key_ideas.map((k, i) => (
                <li key={i}>
                  <strong>{k.idea}</strong>
                  {k.terms.length > 0 && (
                    <div className="ml-2 mt-0.5 text-xs text-slate-500">
                      Термины: {k.terms.join(", ")}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </Block>
        )}

        {c.rule_or_formula && (
          <Block title="Правило / формула">
            <pre className="whitespace-pre-wrap rounded bg-slate-50 p-3 font-mono text-xs">
              {c.rule_or_formula}
            </pre>
          </Block>
        )}

        {c.simple_example && (
          <Block title="Простой пример">{c.simple_example}</Block>
        )}

        {c.schema_or_table && (
          <Block title="Схема / таблица">
            <pre className="whitespace-pre-wrap rounded bg-slate-50 p-3 font-mono text-xs">
              {c.schema_or_table}
            </pre>
          </Block>
        )}

        {c.misconception && (
          <Block title="⚠ Типичное заблуждение">
            <span className="text-amber-800">{c.misconception}</span>
          </Block>
        )}
        {c.common_mistake && (
          <Block title="⚠ Частая ошибка">
            <span className="text-amber-800">{c.common_mistake}</span>
          </Block>
        )}

        {/* Самопроверка */}
        {c.self_check_questions.length > 0 && (
          <Block title="Вопросы самопроверки">
            <ul className="list-disc space-y-1 pl-5">
              {c.self_check_questions.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
          </Block>
        )}

        {/* Практика */}
        {c.practice_tasks.length > 0 && (
          <Block title={`Практические задачи (${c.practice_tasks.length})`}>
            <ol className="space-y-3">
              {c.practice_tasks.map((t, i) => (
                <li key={i} className="rounded-md border border-slate-200 p-3">
                  <div className="flex items-center gap-2 text-xs">
                    <span
                      className={`rounded px-2 py-0.5 font-medium ${
                        t.difficulty === "easy"
                          ? "bg-emerald-100 text-emerald-800"
                          : t.difficulty === "medium"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-rose-100 text-rose-800"
                      }`}
                    >
                      {t.difficulty}
                    </span>
                    <span className="text-slate-500">Задача {i + 1}</span>
                  </div>
                  <p className="mt-1 text-sm">{t.question_text}</p>
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-sky-600">
                      Эталонное решение
                    </summary>
                    <pre className="mt-1 whitespace-pre-wrap rounded bg-slate-50 p-2 font-mono text-xs">
                      {t.reference_solution}
                    </pre>
                  </details>
                  {t.hint && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-xs text-slate-500">
                        Подсказка
                      </summary>
                      <p className="mt-1 text-xs text-slate-600">{t.hint}</p>
                    </details>
                  )}
                </li>
              ))}
            </ol>
          </Block>
        )}

        {/* Мини-тест */}
        {c.mini_test.length > 0 && (
          <Block title={`Мини-тест (${c.mini_test.length})`}>
            <ol className="space-y-3">
              {c.mini_test.map((q, i) => (
                <li key={i} className="rounded-md border border-slate-200 p-3">
                  <p className="text-sm font-medium">
                    {i + 1}. {q.question_text}
                  </p>
                  <ul className="mt-2 space-y-1 text-sm">
                    {q.options.map((opt, j) => (
                      <li
                        key={j}
                        className={`rounded px-2 py-1 ${
                          j === q.correct_index
                            ? "bg-emerald-50 text-emerald-800"
                            : "bg-slate-50"
                        }`}
                      >
                        {String.fromCharCode(65 + j)}. {opt}
                        {j === q.correct_index && (
                          <span className="ml-2 text-xs">✓ верно</span>
                        )}
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2 text-xs text-slate-600">
                    <em>{q.explanation}</em>
                  </p>
                </li>
              ))}
            </ol>
          </Block>
        )}

        {/* Карточки */}
        {c.flashcards.length > 0 && (
          <Block title={`Карточки для повторения (${c.flashcards.length})`}>
            <ul className="grid gap-2 md:grid-cols-2">
              {c.flashcards.map((f, i) => (
                <li
                  key={i}
                  className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm"
                >
                  <div className="font-medium">{f.question}</div>
                  <div className="mt-1 text-xs text-slate-600">{f.answer}</div>
                </li>
              ))}
            </ul>
          </Block>
        )}

        {/* AI uncertainty */}
        {c.ai_uncertainty_notes.length > 0 && (
          <Block title="⚠ Что требует проверки">
            <ul className="list-disc space-y-1 pl-5 text-amber-800">
              {c.ai_uncertainty_notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </Block>
        )}
      </section>
    </main>
  );
}

function Block({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-slate-900">{title}</h2>
      <div className="mt-2 text-sm text-slate-700">{children}</div>
    </div>
  );
}
