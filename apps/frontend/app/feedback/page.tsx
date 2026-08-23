"use client";

/**
 * Sprint P1 (2026-08-23): простая feedback-форма для Кирилла и его родителя.
 *
 * Sprint goal: первая реальная сессия с Kirill. Поверхность feedback
 * минимальна — text + emoji (понятно / скучно / сложно / хочу ещё).
 *
 * Backend endpoint: /api/v1/feedback (см. apps/backend/app/feedback/router.py)
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import { api, ApiError } from "@/lib/api";
import type { User } from "@/types";

type Feeling = "ok" | "boring" | "hard" | "more";

const FEELINGS: { value: Feeling; emoji: string; label: string; tone: string }[] = [
  { value: "ok", emoji: "✅", label: "Было понятно", tone: "emerald" },
  { value: "more", emoji: "🚀", label: "Хочу ещё", tone: "indigo" },
  { value: "boring", emoji: "😐", label: "Скучно", tone: "slate" },
  { value: "hard", emoji: "🧩", label: "Сложно", tone: "amber" },
];

export default function FeedbackPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [feeling, setFeeling] = useState<Feeling | null>(null);
  const [comment, setComment] = useState("");
  const [topicId, setTopicId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.me()
      .then((u) => setUser(u))
      .catch((e: unknown) => {
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
          router.push("/login");
        }
      });
  }, [router]);

  async function submit() {
    if (!feeling) {
      setError("Выбери впечатление");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.feedback({ feeling, comment, topic_id: topicId });
      setDone(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Не удалось отправить");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <main className="prism-shell">
        <Header user={user} backHref="/subjects" backLabel="К предметам" />
        <section className="py-8">
          <div className="prism-frame">
            <div className="prism-layer px-4 pb-7 lg:px-7">
              <div className="prism-card pad text-center">
                <div className="text-5xl">🎉</div>
                <h1 className="prism-title mt-4">Спасибо за фидбек!</h1>
                <p className="mt-3 text-[color:var(--prism-muted)]">
                  Записал. Это поможет сделать AI-Tutor лучше.
                </p>
                <a
                  href="/subjects"
                  className="prism-action primary mt-6 inline-flex"
                >
                  ← Назад к предметам
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="prism-shell">
      <Header user={user} backHref="/subjects" backLabel="К предметам" />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer px-4 pb-7 lg:px-7">
            <div className="prism-card pad">
              <div className="prism-kicker">Sprint P1 — твой фидбек</div>
              <h1 className="prism-title mt-3">Как прошёл урок?</h1>
              <p className="mt-3 max-w-xl text-sm text-[color:var(--prism-muted)]">
                Коротко расскажи — это займёт 30 секунд. Можно выбрать
                эмодзи и написать комментарий (по желанию).
              </p>

              <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                {FEELINGS.map((f) => {
                  const selected = feeling === f.value;
                  return (
                    <button
                      key={f.value}
                      type="button"
                      onClick={() => setFeeling(f.value)}
                      data-feeling={f.value}
                      className={`flex flex-col items-center gap-2 rounded-2xl border p-4 text-sm font-bold transition ${
                        selected
                          ? "border-[color:var(--prism-accent)] bg-[color:var(--prism-panel-solid)]/60 ring-2 ring-[color:var(--prism-accent)]"
                          : "border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/30 hover:border-[color:var(--prism-accent)]/60"
                      }`}
                      aria-pressed={selected}
                    >
                      <span className="text-3xl" aria-hidden="true">{f.emoji}</span>
                      <span>{f.label}</span>
                    </button>
                  );
                })}
              </div>

              <label className="mt-6 block text-sm font-bold text-[color:var(--prism-ink)]">
                Комментарий (по желанию)
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Что было хорошо? Что непонятно? Что хочется изменить?"
                rows={4}
                maxLength={1000}
                aria-label="Комментарий к фидбеку"
                className="mt-2 w-full rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/50 p-3 text-sm text-[color:var(--prism-ink)] placeholder:text-[color:var(--prism-muted)] focus:border-[color:var(--prism-accent)] focus:outline-none"
              />

              <label className="mt-4 block text-sm font-bold text-[color:var(--prism-ink)]">
                ID темы (опционально)
              </label>
              <input
                type="number"
                value={topicId ?? ""}
                onChange={(e) => setTopicId(e.target.value ? Number(e.target.value) : null)}
                placeholder="например, 187 (Среднее арифметическое)"
                aria-label="ID темы, по которой оставлен фидбек"
                className="mt-2 w-full rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/50 p-3 text-sm text-[color:var(--prism-ink)] placeholder:text-[color:var(--prism-muted)] focus:border-[color:var(--prism-accent)] focus:outline-none"
              />

              {error && (
                <div
                  role="alert"
                  className="mt-4 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200"
                >
                  {error}
                </div>
              )}

              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={submit}
                  disabled={submitting || !feeling}
                  data-testid="feedback-submit"
                  className="prism-action primary"
                >
                  {submitting ? "Отправляю…" : "Отправить"}
                </button>
                <a href="/subjects" className="prism-action">
                  Отмена
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}