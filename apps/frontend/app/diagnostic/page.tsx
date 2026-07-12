"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, getToken, setToken } from "@/lib/api";
import type { Subject } from "@/types";

type Q = {
  session_id: number;
  topic_id: number;
  topic_name: string;
  subject_name: string;
  difficulty: number;
  question_text: string;
};

type Result = {
  id: number;
  total_questions: number;
  correct_count: number;
  overall_score: number;
  weak_topics: string | null;
  recommendations: string | null;
  status: string;
};

export default function DiagnosticPage() {
  const router = useRouter();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [question, setQuestion] = useState<Q | null>(null);
  const [answer, setAnswer] = useState("");
  const [correctAnswer, setCorrectAnswer] = useState("");
  const [lastResult, setLastResult] = useState<{ is_correct: boolean } | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) router.push("/login");
    else api.subjects().then(setSubjects).catch(() => {});
  }, [router]);

  async function start(subjectId: number) {
    setBusy(true);
    setError(null);
    setResult(null);
    setLastResult(null);
    try {
      const sess = await api.startDiagnostic(subjectId);
      setSessionId(sess.id);
      const q = await api.nextDiagnosticQuestion(sess.id);
      setQuestion(q);
    } catch (e) {
      setError("Не удалось начать диагностику");
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!question || !sessionId || !answer.trim()) return;
    setBusy(true);
    try {
      const r = await api.submitDiagnosticAnswer(sessionId, {
        topic_id: question.topic_id,
        question_text: question.question_text,
        user_answer: answer,
        correct_answer: question.question_text, // в MVP корректный ответ показывается AI-сгенерированным
      });
      setLastResult(r);
      // Запоминаем эталон (он вернётся в next-question, если AI сохранил)
      setCorrectAnswer(question.question_text);
      setAnswer("");
      // Следующий вопрос
      const q = await api.nextDiagnosticQuestion(sessionId);
      if (q) setQuestion(q);
      else {
        // Закончились вопросы
        const fin = await api.finishDiagnostic(sessionId);
        setResult(fin);
        setSessionId(null);
      }
    } catch (e) {
      setError("Не удалось отправить ответ");
    } finally {
      setBusy(false);
    }
  }

  async function finishEarly() {
    if (!sessionId) return;
    setBusy(true);
    try {
      const fin = await api.finishDiagnostic(sessionId);
      setResult(fin);
      setSessionId(null);
    } catch {
      setError("Не удалось завершить диагностику");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setSessionId(null);
    setQuestion(null);
    setResult(null);
    setLastResult(null);
    setAnswer("");
    setCorrectAnswer("");
  }

  return (
    <main className="mx-auto max-w-3xl p-6">
      <header className="border-b border-slate-200 pb-3">
        <Link href="/subjects" className="text-sm text-sky-600 hover:underline">
          ← На главную
        </Link>
        <h1 className="mt-1 text-2xl font-bold">Диагностика</h1>
        <p className="text-sm text-slate-600">
          Пройди короткий тест — узнаешь, что стоит повторить
        </p>
      </header>

      {error && <div className="mt-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

      {!sessionId && !result && (
        <section className="mt-6">
          <h2 className="text-lg font-semibold">Выбери предмет</h2>
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
            {subjects.map((s) => (
              <button
                key={s.id}
                disabled={busy}
                onClick={() => start(s.id)}
                className="rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-sky-300 hover:shadow-md disabled:opacity-50"
              >
                <div className="text-3xl">{s.icon || "📘"}</div>
                <div className="mt-2 font-semibold">{s.name}</div>
              </button>
            ))}
          </div>
        </section>
      )}

      {question && !result && (
        <section className="mt-6">
          <div className="text-xs uppercase tracking-wide text-slate-500">
            {question.subject_name} · {question.topic_name} · сложность {question.difficulty}/5
          </div>
          <div className="mt-3 whitespace-pre-wrap rounded-xl border border-slate-200 bg-white p-4 text-slate-900 shadow-sm">
            {question.question_text.replace(/<[^>]+>/g, "")}
          </div>

          {lastResult && (
            <div
              className={`mt-3 rounded-md p-3 text-sm ${
                lastResult.is_correct ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-900"
              }`}
            >
              {lastResult.is_correct ? "Верно" : "Ответ принят"} — следующий вопрос ↓
            </div>
          )}

          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Твой ответ…"
            rows={4}
            className="mt-3 block w-full rounded-md border border-slate-300 bg-white p-3"
            disabled={busy}
          />
          <div className="mt-3 flex gap-2">
            <button
              onClick={submit}
              disabled={busy || !answer.trim()}
              className="rounded-md bg-sky-600 px-4 py-2 font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
            >
              Ответить
            </button>
            <button
              onClick={finishEarly}
              disabled={busy}
              className="rounded-md bg-slate-200 px-4 py-2 text-slate-700 hover:bg-slate-300 disabled:opacity-50"
            >
              Завершить
            </button>
          </div>
        </section>
      )}

      {result && (
        <section className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-6">
          <h2 className="text-xl font-bold text-emerald-900">Готово!</h2>
          <p className="mt-2 text-sm text-emerald-800">
            Правильных ответов: {result.correct_count} из {result.total_questions} (
            {Math.round(result.overall_score * 100)}%)
          </p>
          {result.recommendations && (
            <div className="mt-4 whitespace-pre-wrap rounded-md bg-white p-4 text-sm text-slate-800 shadow-sm">
              {result.recommendations}
            </div>
          )}
          <div className="mt-4 flex gap-2">
            <button
              onClick={reset}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
            >
              Пройти ещё раз
            </button>
            <Link
              href="/subjects"
              className="rounded-md bg-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-300"
            >
              На главную
            </Link>
          </div>
        </section>
      )}
    </main>
  );
}