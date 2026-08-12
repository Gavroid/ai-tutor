"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import Header from "@/components/Header";
import type { Subject, User } from "@/types";

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
  const [user, setUser] = useState<User | null>(null);
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
    api.me().then(setUser).catch(() => router.push("/login"));
    api.subjects().then(setSubjects).catch(() => {});
  }, [router]);

  async function start(subjectId: number) {
    setBusy(true); setError(null); setResult(null); setLastResult(null);
    try {
      const sess = await api.startDiagnostic(subjectId);
      setSessionId(sess.id);
      const q = await api.nextDiagnosticQuestion(sess.id);
      setQuestion(q);
    } catch { setError("Не удалось начать диагностику"); }
    finally { setBusy(false); }
  }

  async function submit() {
    if (!question || !sessionId || !answer.trim()) return;
    setBusy(true);
    try {
      const r = await api.submitDiagnosticAnswer(sessionId, { topic_id: question.topic_id, question_text: question.question_text, user_answer: answer, correct_answer: question.question_text });
      setLastResult(r);
      setCorrectAnswer(question.question_text);
      setAnswer("");
      const q = await api.nextDiagnosticQuestion(sessionId);
      if (q) setQuestion(q);
      else { const fin = await api.finishDiagnostic(sessionId); setResult(fin); setSessionId(null); }
    } catch { setError("Не удалось отправить ответ"); }
    finally { setBusy(false); }
  }

  async function finishEarly() {
    if (!sessionId) return;
    setBusy(true);
    try { const fin = await api.finishDiagnostic(sessionId); setResult(fin); setSessionId(null); }
    catch { setError("Не удалось завершить диагностику"); }
    finally { setBusy(false); }
  }

  function reset() { setSessionId(null); setQuestion(null); setResult(null); setLastResult(null); setAnswer(""); setCorrectAnswer(""); }

  return (
    <main className="prism-shell diagnostic-console min-h-dvh">
      <Header user={user} backHref="/subjects" title="Диагностика" />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer p-5 lg:p-10">
        <div className="grid gap-5 lg:grid-cols-[0.9fr_1.25fr]">
          <aside className="prism-card pad glow">
            <div className="prism-kicker">Диагностика</div>
            <h1 className="mt-4 text-4xl font-black tracking-[-0.06em] text-[color:var(--prism-ink)] sm:text-6xl">Короткий тест перед маршрутом</h1>
            <p className="mt-4 text-sm leading-6 text-[color:var(--prism-muted)]">Выбери предмет, ответь на несколько вопросов — система подскажет, что стоит повторить.</p>
            {error && <div className="mt-5 rounded-2xl border border-rose-300/30 bg-rose-400/10 px-4 py-3 text-sm font-bold text-rose-200">{error}</div>}
          </aside>

          <section className="prism-card pad">
            {!sessionId && !result && (
              <>
                <div className="prism-kicker">Выбери предмет</div>
                <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
                  {subjects.map((s) => (
                    <button key={s.id} disabled={busy} onClick={() => start(s.id)} className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-4 text-left transition hover:border-[color:var(--prism-accent)] disabled:opacity-50">
                      <div className="prism-mark grid place-items-center text-xl text-white">{s.icon || "📘"}</div>
                      <div className="mt-3 text-sm font-black text-[color:var(--prism-ink)]">{s.name}</div>
                    </button>
                  ))}
                </div>
              </>
            )}

            {question && !result && (
              <div>
                <div className="text-xs font-black uppercase tracking-[0.16em] text-[color:var(--prism-muted)]">{question.subject_name} · {question.topic_name} · сложность {question.difficulty}/5</div>
                <div className="mt-3 whitespace-pre-wrap rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-4 text-sm leading-6 text-[color:var(--prism-ink)]">{question.question_text.replace(/<[^>]+>/g, "")}</div>
                {lastResult && <div className={`mt-3 rounded-2xl border px-4 py-3 text-sm font-bold ${lastResult.is_correct ? "border-emerald-300/30 bg-emerald-400/10 text-emerald-100" : "border-amber-300/30 bg-amber-400/10 text-amber-100"}`}>{lastResult.is_correct ? "Верно" : "Ответ принят"} — следующий вопрос ↓</div>}
                <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Твой ответ…" rows={4} className="prism-input mt-3 min-h-[120px]" disabled={busy} />
                <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                  <button onClick={submit} disabled={busy || !answer.trim()} className="prism-action primary">Ответить</button>
                  <button onClick={finishEarly} disabled={busy} className="prism-action">Завершить</button>
                </div>
              </div>
            )}

            {result && (
              <section className="rounded-3xl border border-emerald-300/30 bg-emerald-400/10 p-5">
                <h2 className="text-3xl font-black text-[color:var(--prism-ink)]">Готово</h2>
                <p className="mt-2 text-sm text-[color:var(--prism-muted)]">Правильных ответов: {result.correct_count} из {result.total_questions} ({Math.round(result.overall_score * 100)}%)</p>
                {result.recommendations && <div className="mt-4 whitespace-pre-wrap rounded-2xl bg-black/10 p-4 text-sm text-[color:var(--prism-ink)]">{result.recommendations}</div>}
                <div className="mt-4 flex flex-col gap-2 sm:flex-row"><button onClick={reset} className="prism-action primary">Пройти ещё раз</button><Link href="/subjects" className="prism-action">На главную</Link></div>
              </section>
            )}
          </section>
        </div>
          </div>
        </div>
      </section>
    </main>
  );
}
