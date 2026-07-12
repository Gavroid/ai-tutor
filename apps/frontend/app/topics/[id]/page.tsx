"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, getToken } from "@/lib/api";
import { useChatStream } from "@/lib/ws-chat";
import { renderMarkdown } from "@/lib/markdown";
import SafeMarkdown from "@/components/SafeMarkdown";
import type { Topic, ChatMsg } from "@/types";

type Exercise = {
  question_text: string;
  options: string[] | null;
  type: string;
  correct_answer?: string; // скрыт от ученика
  explanation?: string;
};

// LocalStorage ключ для автосохранения урока (Sprint 7.3)
function draftKey(topicId: number): string {
  return `ai-tutor:draft:${topicId}`;
}

interface SavedDraft {
  msgs: ChatMsg[];
  exercise: Exercise | null;
  userAnswer: string;
  input: string;
  checkResult: {
    is_correct: boolean;
    score: number;
    first_error: string | null;
    explanation: string;
    hint_level: number;
  } | null;
  savedAt: number;
}

export default function TopicPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const topicId = Number(params?.id);

  const [topic, setTopic] = useState<Topic | null>(null);
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [userAnswer, setUserAnswer] = useState("");
  const [checkResult, setCheckResult] = useState<null | {
    is_correct: boolean;
    score: number;
    first_error: string | null;
    explanation: string;
    hint_level: number;
  }>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const chat = useChatStream(getToken());

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    if (!topicId || Number.isNaN(topicId)) return;
    api.topic(topicId).then(setTopic).catch(() => router.push("/subjects"));
  }, [topicId, router]);

  // Sprint 7.3 — восстановление черновика урока (критично при T1D).
  // Приоритет: серверный черновик (свежее) > localStorage.
  const [draftRestored, setDraftRestored] = useState(false);
  const [showRestorePrompt, setShowRestorePrompt] = useState(false);
  useEffect(() => {
    if (!topicId || !getToken() || draftRestored) return;
    let cancelled = false;
    (async () => {
      // 1) пытаемся серверный
      const srv = await api.topicDraftLoad(topicId);
      if (cancelled) return;
      if (srv.ok && srv.payload) {
        const d = srv.payload as Partial<SavedDraft>;
        if (d.msgs && Array.isArray(d.msgs) && d.msgs.length > 0) {
          setShowRestorePrompt(true);
          // Сохраним в стороне, чтобы пользователь мог решить.
          (window as Window & { __aiTutorPendingDraft?: SavedDraft }).__aiTutorPendingDraft = {
            msgs: d.msgs as ChatMsg[],
            exercise: d.exercise ?? null,
            userAnswer: d.userAnswer ?? "",
            input: d.input ?? "",
            checkResult: d.checkResult ?? null,
            savedAt: Date.now(),
          };
        }
      }
      // 2) localStorage — восстанавливаем всегда (даже если сервер дал 404)
      const ls = localStorage.getItem(draftKey(topicId));
      if (ls) {
        try {
          const d = JSON.parse(ls) as SavedDraft;
          if (!cancelled && d && Array.isArray(d.msgs)) {
            setMsgs(d.msgs);
            setExercise(d.exercise ?? null);
            setUserAnswer(d.userAnswer ?? "");
            setInput(d.input ?? "");
            setCheckResult(d.checkResult ?? null);
          }
        } catch {
          // ignore corrupted draft
        }
      }
      setDraftRestored(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [topicId, draftRestored]);

  // Sprint 7.3 — автосохранение в localStorage каждые ~5 сек (debounce) + sync на сервер каждые ~15 сек.
  useEffect(() => {
    if (!topicId || !draftRestored) return;
    const ls = setInterval(() => {
      const payload: SavedDraft = {
        msgs,
        exercise,
        userAnswer,
        input,
        checkResult,
        savedAt: Date.now(),
      };
      try {
        localStorage.setItem(draftKey(topicId), JSON.stringify(payload));
      } catch {
        // quota exceeded — пропускаем
      }
    }, 5_000);
    const srv = setInterval(() => {
      if (msgs.length === 0 && !exercise && !userAnswer && !input) return;
      const payload: Record<string, unknown> = {
        msgs,
        exercise,
        userAnswer,
        input,
        checkResult,
        savedAt: Date.now(),
      };
      api.topicDraftSave(topicId, payload).catch(() => {
        // Не блокируем UI, если сервер недоступен — localStorage компенсирует.
      });
    }, 15_000);
    return () => {
      clearInterval(ls);
      clearInterval(srv);
    };
  }, [topicId, draftRestored, msgs, exercise, userAnswer, input, checkResult]);

  useEffect(() => {
    return () => chat.cancel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs]);

  function send() {
    const text = input.trim();
    if (!text || busy) return;
    const next: ChatMsg[] = [...msgs, { role: "user", content: text }];
    setMsgs(next);
    setInput("");
    setBusy(true);

    // Добавляем пустое сообщение ассистента, которое будем наполнять chunks
    const assistantIdx = next.length;
    setMsgs((m) => [...m, { role: "assistant", content: "" }]);

    chat.send(next, topicId, {
      onChunk: (chunk) => {
        setMsgs((m) => {
          const updated = [...m];
          if (updated[assistantIdx]) {
            updated[assistantIdx] = {
              ...updated[assistantIdx],
              content: updated[assistantIdx].content + chunk,
            };
          }
          return updated;
        });
      },
      onDone: () => {
        setBusy(false);
      },
      onError: (msg) => {
        setMsgs((m) => {
          const updated = [...m];
          if (updated[assistantIdx]) {
            updated[assistantIdx] = {
              ...updated[assistantIdx],
              content:
                (updated[assistantIdx].content || "") +
                "\n\n[Ошибка: " +
                msg +
                "]",
            };
          }
          return updated;
        });
        setBusy(false);
      },
    });
  }

  async function explain() {
    if (busy) return;
    setBusy(true);
    try {
      const r = await api.aiExplain(topicId);
      setMsgs((m) => [...m, { role: "assistant", content: r.content }]);
    } catch {
      setMsgs((m) => [...m, { role: "assistant", content: "[ошибка] Не удалось получить объяснение." }]);
    } finally {
      setBusy(false);
    }
  }

  async function generate() {
    if (busy) return;
    setBusy(true);
    setExercise(null);
    setCheckResult(null);
    setUserAnswer("");
    try {
      const r = await api.aiGenerate(topicId, topic?.difficulty ?? 2);
      setExercise({
        question_text: r.question_text,
        options: r.options,
        type: r.type,
        correct_answer: r.correct_answer,
        explanation: r.explanation,
      });
    } catch {
      alert("Не удалось сгенерировать задание");
    } finally {
      setBusy(false);
    }
  }

  async function checkAnswer() {
    if (!exercise?.correct_answer) return;
    setBusy(true);
    try {
      const r = await api.aiCheck(exercise.question_text, exercise.correct_answer, userAnswer);
      setCheckResult(r);
      // Записываем попытку в прогресс
      api
        .recordAttempt({
          topic_id: topicId,
          question_text: exercise.question_text,
          user_answer: userAnswer,
          correct_answer: exercise.correct_answer,
          is_correct: r.is_correct,
          score: r.score,
          feedback: r.first_error ?? r.explanation,
        })
        .catch(() => {});
    } catch {
      alert("Не удалось проверить ответ");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex h-screen max-w-3xl flex-col p-4">
      <header className="border-b border-slate-200 pb-3">
        <Link href="/subjects" className="text-sm text-sky-600 hover:underline">
          ← Все предметы
        </Link>
        <h1 className="mt-1 text-xl font-bold">{topic?.name || "Тема"}</h1>
      </header>

      <section className="mt-4 flex gap-2">
        <button
          onClick={explain}
          disabled={busy}
          className="rounded-lg bg-sky-100 px-3 py-1.5 text-sm font-medium text-sky-800 hover:bg-sky-200 disabled:opacity-50"
        >
          Объясни тему
        </button>
        <button
          onClick={generate}
          disabled={busy}
          className="rounded-lg bg-emerald-100 px-3 py-1.5 text-sm font-medium text-emerald-800 hover:bg-emerald-200 disabled:opacity-50"
        >
          Дай задание
        </button>
      </section>

      {exercise && (
        <section className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <div className="text-xs uppercase tracking-wide text-emerald-700">Задание</div>
          <p className="mt-1 whitespace-pre-wrap text-slate-900">{exercise.question_text}</p>
          {exercise.options && exercise.options.length > 0 && (
            <div className="mt-3 space-y-1">
              {exercise.options.map((opt) => (
                <button
                  key={opt}
                  onClick={() => setUserAnswer(opt)}
                  className={`block w-full rounded-md border px-3 py-2 text-left text-sm ${
                    userAnswer === opt
                      ? "border-emerald-500 bg-white"
                      : "border-slate-300 bg-white hover:border-emerald-300"
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}
          {exercise.type === "numeric" || exercise.type === "text" ? (
            <input
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              placeholder={exercise.type === "numeric" ? "Числовой ответ" : "Текстовый ответ"}
              className="mt-3 block w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            />
          ) : null}
          <button
            onClick={checkAnswer}
            disabled={busy || !userAnswer}
            className="mt-3 rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            Проверить
          </button>
          {checkResult && (
            <div
              className={`mt-3 rounded-md p-3 text-sm ${
                checkResult.is_correct ? "bg-emerald-100 text-emerald-900" : "bg-rose-100 text-rose-900"
              }`}
            >
              <div className="font-semibold">
                {checkResult.is_correct ? "Верно!" : "Есть ошибка"} (оценка {Math.round(checkResult.score * 100)}%)
              </div>
              {checkResult.first_error && <div className="mt-1">Шаг ошибки: {checkResult.first_error}</div>}
              <div className="mt-1">{checkResult.explanation}</div>
            </div>
          )}
        </section>
      )}

      <section ref={scrollRef} className="mt-4 flex-1 space-y-3 overflow-y-auto rounded-xl bg-slate-50 p-4">
        {msgs.length === 0 && (
          <p className="text-sm text-slate-500">
            Напиши вопрос репетитору или нажми «Объясни тему» / «Дай задание».
          </p>
        )}
        {msgs.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm shadow-sm ${
              m.role === "user"
                ? "ml-auto bg-sky-600 text-white"
                : "mr-auto bg-white text-slate-900"
            }`}
          >
            {m.role === "user" ? (
              <span className="whitespace-pre-wrap">{m.content}</span>
            ) : (
              // Sprint 7.1: AI-сообщения рендерим Markdown → безопасный HTML.
              // streaming=true только для последнего ассистентского сообщения, которое
              // ещё не подтверждено `done` — даёт typewriter-эффект.
              <SafeMarkdown
                text={m.content}
                streaming={i === msgs.length - 1 && busy && m.role === "assistant"}
              />
            )}
          </div>
        ))}
        {busy && (
          <div className="mr-auto flex items-center gap-1 rounded-2xl bg-white px-4 py-2 text-sm text-slate-500 shadow-sm">
            {chat.status === "reconnecting" ? (
              <>
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-amber-500" />
                <span className="ml-1">Переподключение к AI…</span>
              </>
            ) : chat.status === "error" ? (
              <>
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-rose-500" />
                <span className="ml-1">Ошибка соединения</span>
              </>
            ) : (
              <>
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: "0ms" }} />
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: "150ms" }} />
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: "300ms" }} />
                <span className="ml-1">AI думает…</span>
              </>
            )}
          </div>
        )}
      </section>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="mt-3 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Задай вопрос репетитору…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
          disabled={busy}
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-lg bg-sky-600 px-4 py-2 font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
        >
          Отправить
        </button>
      </form>
    </main>
  );
}