"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, getToken, ApiError } from "@/lib/api";
import { useChatStream } from "@/lib/ws-chat";
import { renderMarkdown } from "@/lib/markdown";
import SafeMarkdown from "@/components/SafeMarkdown";
import type { Topic, ChatMsg } from "@/types";

// Sprint 12: helper для извлечения error-сообщения.
// ApiError содержит status + message. Generic Error — только message.
// Иначе — fallback «Неизвестная ошибка».
function extractErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 503 || err.status === 504) {
      return `AI временно недоступен (HTTP ${err.status}). Попробуй позже.`;
    }
    if (err.status === 429) {
      return "Слишком много запросов. Подожди минуту и попробуй снова.";
    }
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Неизвестная ошибка";
}

// Sprint 15.4: copyToClipboard — для кнопки «Копировать» в chat.
// В современных браузерах navigator.clipboard.writeText есть всегда.
// Fallback для старых: textarea + execCommand.
async function copyToClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    // Fallback для неподдерживаемых браузеров / insecure context.
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "absolute";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } finally {
      document.body.removeChild(ta);
    }
  }
}

type Exercise = {
  exercise_id: number; // Pilot Core: opaque server id
  question_text: string;
  options: string[] | null;
  type: string;
  // Pilot Core: correct_answer НЕ приходит от API до submit. Хранится локально
  // только для UI, нигде не передаётся в /progress/attempts.
  correct_answer?: string;
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
  // Sprint 15.5: подтверждение очистки чата (чтобы ребёнок случайно не потерял).
  const [showClearConfirm, setShowClearConfirm] = useState(false);
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
    // Sprint 4.3.1: error_type от judge, передаётся в hint для context-aware подсказок.
    error_type?: string | null;
  }>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const chat = useChatStream(getToken());
  const voiceEnabled = process.env.NEXT_PUBLIC_VOICE_ENABLED === "1";

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
            // Pilot Core: draft может содержать exercise в legacy-формате
            // (без opaque exercise_id). Такой draft использовать нельзя —
            // принудительно очищаем, чтобы user получил новый exercise_id.
            const ex = d.exercise as Exercise | null | undefined;
            if (ex && typeof ex.exercise_id === "number") {
              setExercise(ex);
            } else {
              setExercise(null);
            }
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
      setMsgs((m) => [
        ...m,
        { role: "assistant", content: r.content, sources: r.sources },
      ]);
    } catch (err) {
      // Sprint 12: T1D-friendly error UI (вместо текстовой inline-ошибки).
      setMsgs((m) => [
        ...m,
        {
          role: "assistant",
          content:
            "🤖 AI временно недоступен. Попробуй ещё раз через несколько секунд.",
          error: extractErrorMessage(err),
        },
      ]);
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
      // Pilot Core Stage 1 — secure flow: server-owned truth, opaque id.
      const r = await api.v2GenerateExercise({
        topic_id: topicId,
        difficulty: topic?.difficulty ?? 2,
      });
      setExercise({
        exercise_id: r.exercise_id,
        question_text: r.question_text,
        options: r.options,
        type: r.type,
        // correct_answer и explanation придут ПОСЛЕ submit (server-trusted).
      });
    } catch {
      alert("Не удалось сгенерировать задание");
    } finally {
      setBusy(false);
    }
  }

  async function checkAnswer() {
    if (!exercise?.exercise_id) return;
    setBusy(true);
    try {
      // Pilot Core: client отправляет только exercise_id + user_answer.
      // server-trusted is_correct/score/explanation возвращаются сразу.
      const r = await api.v2SubmitAnswer(exercise.exercise_id, userAnswer);
      setCheckResult({
        is_correct: r.is_correct,
        score: r.score,
        first_error: null,
        explanation: r.explanation,
        hint_level: 1,
        // Sprint 4.3.1: error_type для context-aware hints.
        error_type: r.error_type ?? null,
      });
    } catch {
      alert("Не удалось проверить ответ");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex h-screen max-w-3xl flex-col p-3 sm:p-4">
      <header className="border-b border-slate-200 pb-3">
        <Link href="/subjects" className="text-sm text-sky-600 hover:underline">
          ← Все предметы
        </Link>
        <h1 className="mt-1 text-xl font-bold">{topic?.name || "Тема"}</h1>
      </header>

      <section className="mt-4 flex flex-wrap gap-2">
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

        {/* Sprint 15.5: кнопка Clear chat (с confirm для safety).
            T1D-friendly: показываем вторичную кнопку сначала — очистить чат,
            не send. Confirm dialog перед очисткой. */}
        {msgs.length > 0 && !showClearConfirm && (
          <button
            type="button"
            onClick={() => setShowClearConfirm(true)}
            aria-label="Очистить чат"
            className="rounded-lg bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50"
          >
            🧹 Очистить
          </button>
        )}
        {showClearConfirm && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5">
            <span className="text-xs text-amber-800">Удалить всю историю?</span>
            <button
              type="button"
              onClick={() => {
                setMsgs([]);
                setShowClearConfirm(false);
              }}
              className="rounded bg-amber-600 px-2 py-0.5 text-xs font-semibold text-white hover:bg-amber-700"
            >
              Да, удалить
            </button>
            <button
              type="button"
              onClick={() => setShowClearConfirm(false)}
              className="rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700 hover:bg-slate-300"
            >
              Отмена
            </button>
          </div>
        )}
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
              {/* Sprint 4.2.3: показываем правильный ответ если score < 0.6 */}
              {!checkResult.is_correct && checkResult.score < 0.6 && exercise && (
                <details className="mt-2 rounded-md bg-white/70 p-2">
                  <summary className="cursor-pointer text-xs font-semibold text-rose-900">
                    📖 Покажи правильный ответ
                  </summary>
                  <div className="mt-2 text-sm">
                    <div>
                      <strong>Твой ответ:</strong> {userAnswer || "(пусто)"}
                    </div>
                    <div className="mt-1">
                      <strong>Правильный:</strong> {exercise.correct_answer || "(недоступен)"}
                    </div>
                  </div>
                </details>
              )}
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
              <>
                <SafeMarkdown
                  text={m.content}
                  streaming={i === msgs.length - 1 && busy && m.role === "assistant"}
                />
                {/* Sprint 4.1.3: индикатор источника RAG (📖 Источник) */}
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs">
                    <div className="mb-1 font-semibold text-amber-800">📖 Источник:</div>
                    <ul className="space-y-1">
                      {m.sources.map((s, idx) => (
                        <li key={idx} className="text-amber-900">
                          {s.material_title}
                          {s.page_number != null && `, стр. ${s.page_number}`}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {/* Sprint 15.4: кнопка copy для последнего assistant msg.
                    Не показываем во время streaming чтобы не копировать черновик.
                    T1D-friendly: крупная (44px) для слабой моторики. */}
                {i === msgs.length - 1 &&
                  m.role === "assistant" &&
                  !busy &&
                  m.content && (
                    <button
                      type="button"
                      onClick={() => copyToClipboard(m.content)}
                      aria-label="Копировать ответ"
                      className="mt-1 inline-flex items-center gap-1 rounded-md bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
                    >
                      📋 Копировать
                    </button>
                  )}
              </>
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
        className="mt-3 flex flex-col gap-1"
      >
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            // Sprint 15.1: Enter отправляет, Shift+Enter новая строка.
            // Для plain input Enter просто submit формы — это OK.
            placeholder="Задай вопрос репетитору…"
            maxLength={500}
            aria-describedby="input-hint"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
            disabled={busy}
          />
          {voiceEnabled && (
            <VoiceMicButton
              disabled={busy}
              onTranscript={(text) => setInput((prev) => (prev ? prev + " " : "") + text)}
              onError={(msg) => alert("Микрофон: " + msg)}
            />
          )}
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="rounded-lg bg-sky-600 px-4 py-2 font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
          >
            {/* Sprint 15.1: визуальный feedback для disabled состояния */}
            {busy ? "⏳" : "Отправить"}
          </button>
        </div>
        {/* Sprint 15.1: counter для длины input — помогает детям контролировать.
            Большинство сообщений должны быть короткими вопросами. */}
        <div
          id="input-hint"
          className="flex items-center justify-between text-xs text-slate-500"
        >
          <span>Enter — отправить, Shift+Enter — новая строка</span>
          <span
            className={
              input.length > 400 ? "font-bold text-amber-600" : ""
            }
          >
            {input.length}/500
          </span>
        </div>
      </form>
    </main>
  );
}

/**
 * Sprint 7.2 — кнопка голосового ввода.
 * Использует MediaRecorder API в браузере → POST /api/v1/voice/transcribe.
 *
 * Особенности для T1D-ученика:
 * - Крупная кнопка (48px+ tap target)
 * - Явная индикация записи (красный пульсирующий круг + таймер)
 * - Отмена одним тапом
 * - Graceful fallback, если API не настроен
 */
function VoiceMicButton({
  disabled,
  onTranscript,
  onError,
}: {
  disabled: boolean;
  onTranscript: (text: string) => void;
  onError: (msg: string) => void;
}) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  async function start() {
    if (recording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        try {
          const r = await api.voiceTranscribe(blob);
          if (r.text?.trim()) onTranscript(r.text.trim());
          else onError("Не удалось распознать речь");
        } catch (e: unknown) {
          onError((e as Error)?.message || "Ошибка распознавания");
        }
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
      setSeconds(0);
      timerRef.current = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch (e: unknown) {
      const msg = (e as Error)?.message?.includes("Permission")
        ? "Нет доступа к микрофону"
        : "Микрофон недоступен";
      onError(msg);
    }
  }

  function stop() {
    if (!recording) return;
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    setRecording(false);
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  // Cleanup on unmount
  useEffect(
    () => () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
      const r = recorderRef.current;
      if (r && r.state !== "inactive") {
        try {
          r.stop();
        } catch {
          /* ignore */
        }
      }
    },
    [],
  );

  return (
    <button
      type="button"
      onClick={() => (recording ? stop() : start())}
      disabled={disabled}
      aria-label={recording ? "Остановить запись" : "Записать голосовое сообщение"}
      title={
        typeof navigator !== "undefined" && !navigator.mediaDevices
          ? "Микрофон не поддерживается"
          : recording
            ? `Идёт запись… ${seconds}с`
            : "Записать голос"
      }
      className={`relative h-11 w-11 shrink-0 rounded-full text-2xl transition ${
        recording
          ? "animate-pulse bg-rose-500 text-white shadow-lg shadow-rose-500/40"
          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
      } disabled:opacity-50`}
    >
      {recording ? "⏹" : "🎤"}
      {recording && (
        <span className="absolute -right-2 -top-1 rounded bg-rose-700 px-1 text-[10px] font-semibold text-white">
          {seconds}s
        </span>
      )}
    </button>
  );
}