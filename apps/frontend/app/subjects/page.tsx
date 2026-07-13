"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, getToken, setToken, ApiError } from "@/lib/api";
import type { Subject, User } from "@/types";

type RecItem = {
  topic_id: number;
  topic_name: string;
  subject_id: number;
  subject_name: string;
  mastery_score: number;
  attempts_count: number;
  correct_count: number;
};

export default function HomePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [aiOk, setAiOk] = useState<boolean | null>(null);
  const [aiModel, setAiModel] = useState<string | null>(null);
  const [review, setReview] = useState<RecItem[]>([]);
  const [dueReview, setDueReview] = useState<
    Array<{
      topic_id: number;
      topic_name: string;
      subject_name: string;
      mastery_score: number;
      days_overdue: number;
    }>
  >([]);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    api
      .me()
      .then(setUser)
      .catch((err: unknown) => {
        // Sprint 2.6 — стираем токен ТОЛЬКО при 401/403 (реально невалидный).
        // При 5xx или network-glitch оставляем токен, чтобы пользователь
        // не вылетал на /login при временных сбоях.
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          setToken(null);
          router.push("/login");
        } else {
          // Не 401 — не трогаем токен. user останется null, страница покажет
          // "Привет!" без имени (это безопасно).
          console.warn("api.me() failed (non-auth):", err);
        }
      });
    api.subjects().then(setSubjects).catch(() => {});
    api.aiPing().then((r) => { setAiOk(r.ok); setAiModel(r.model); }).catch(() => setAiOk(false));
    api.recommendReview().then(setReview).catch(() => {});
    api.dueForReview(10).then(setDueReview).catch(() => {});
  }, [router]);

  function logout() {
    setToken(null);
    router.push("/login");
  }

  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="flex items-center justify-between border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold">Привет{user ? `, ${user.display_name}` : ""}!</h1>
          <p className="text-sm text-slate-600">
            Выбери предмет и начни заниматься
            {aiOk === true && aiModel && (
              <span className="ml-2 inline-block rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800">
                AI: {aiModel}
              </span>
            )}
            {aiOk === false && (
              <span className="ml-2 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
                AI недоступен (mock)
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/diagnostic"
            className="rounded-md bg-emerald-100 px-3 py-1.5 text-sm font-medium text-emerald-800 hover:bg-emerald-200"
          >
            Диагностика
          </Link>
          <Link
            href="/link-parent"
            className="rounded-md bg-violet-100 px-3 py-1.5 text-sm font-medium text-violet-800 hover:bg-violet-200"
          >
            Привязать родителя
          </Link>
          {user?.role === "parent" && (
            <Link
              href="/parents"
              className="rounded-md bg-pink-100 px-3 py-1.5 text-sm font-medium text-pink-800 hover:bg-pink-200"
            >
              Родительский кабинет
            </Link>
          )}
          {user?.role === "admin" && (
            <Link
              href="/admin"
              className="rounded-md bg-amber-100 px-3 py-1.5 text-sm font-medium text-amber-800 hover:bg-amber-200"
            >
              Админ-панель
            </Link>
          )}
          {(user?.role === "teacher" || user?.role === "admin") && (
            <Link
              href="/teacher"
              className="rounded-md bg-sky-100 px-3 py-1.5 text-sm font-medium text-sky-800 hover:bg-sky-200"
            >
              Учительская
            </Link>
          )}
          <button onClick={logout} className="rounded-md bg-slate-100 px-3 py-1.5 text-sm hover:bg-slate-200">
            Выйти
          </button>
        </div>
      </header>

      {dueReview.length > 0 && (
        <section className="mt-6 rounded-xl border border-violet-200 bg-violet-50 p-4">
          <h2 className="text-base font-semibold text-violet-900">🔄 Сегодня к повторению</h2>
          <p className="mt-1 text-sm text-violet-800">
            Интервальное повторение помогает закрепить тему надолго. Не обязательно
            все сразу — начни с просроченных.
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {dueReview.slice(0, 5).map((d) => (
              <li key={d.topic_id}>
                <Link
                  href={`/topics/${d.topic_id}`}
                  className="flex items-center justify-between rounded-md px-2 py-1 hover:bg-violet-100"
                >
                  <span>
                    <span className="text-violet-700">{d.subject_name}:</span>{" "}
                    {d.topic_name}
                  </span>
                  <span className="text-xs text-violet-700">
                    {d.days_overdue > 0
                      ? `просрочено на ${d.days_overdue}д`
                      : d.days_overdue === 0
                        ? "сегодня"
                        : `через ${-d.days_overdue}д`}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {review.length > 0 && (
        <section className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <h2 className="text-base font-semibold text-amber-900">Стоит повторить</h2>
          <p className="mt-1 text-sm text-amber-800">
            Эти темы давались труднее всего. Пара упражнений — и будет лучше.
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {review.slice(0, 5).map((r) => (
              <li key={r.topic_id}>
                <Link
                  href={`/topics/${r.topic_id}`}
                  className="flex items-center justify-between rounded-md px-2 py-1 hover:bg-amber-100"
                >
                  <span>
                    <span className="text-amber-700">{r.subject_name}:</span> {r.topic_name}
                  </span>
                  <span className="text-xs text-amber-700">
                    уверенность {Math.round(r.mastery_score * 100)}%
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Предметы</h2>
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
          {subjects.map((s) => (
            <Link
              key={s.id}
              href={`/subjects/${s.id}`}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-sky-300 hover:shadow-md"
            >
              <div className="text-3xl">{s.icon || "📘"}</div>
              <div className="mt-2 font-semibold">{s.name}</div>
              {s.description && <div className="mt-1 line-clamp-2 text-xs text-slate-500">{s.description}</div>}
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}