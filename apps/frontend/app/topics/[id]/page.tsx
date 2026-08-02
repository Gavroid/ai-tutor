"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, getToken, ApiError } from "@/lib/api";
import Header from "@/components/Header";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import SafeMarkdown from "@/components/SafeMarkdown";
import PauseButton from "@/components/PauseButton";
import SessionTimer from "@/components/SessionTimer";
import CGMStatus from "@/components/CGMStatus";
import { playCompletionCue } from "@/lib/audio-cue";
import type { Topic, TopicFollowup, ChatMsg, User } from "@/types";

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

  const [user, setUser] = useState<User | null>(null);
  const [topic, setTopic] = useState<Topic | null>(null);
  const [followups, setFollowups] = useState<TopicFollowup[]>([]);
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  // Sprint 15.5: подтверждение очистки чата (чтобы ребёнок случайно не потерял).
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Sprint 42: T1D recovery mode (timing-based, opt-in через backend).
  // Если недавно была hypo/hyper пауза → recovery_mode=true → badge показывается.
  const [recommendNext, setRecommendNext] = useState<{
    recovery_mode: boolean;
    recovery_reason: string | null;
    minutes_since_pause: number | null;
  } | null>(null);

  // Sprint 23: audio cue когда AI завершил ответ (новое ассистентское сообщение).
  // Использует Web Audio API, opt-in (T1D-friendly: дети с гипо/гипер могут
  // не смотреть на экран постоянно, звук помогает услышать завершение).
  const prevMsgsCountRef = useRef(0);
  useEffect(() => {
    // Срабатывает только когда добавляется НОВОЕ assistant-сообщение.
    const last = msgs[msgs.length - 1];
    if (
      msgs.length > prevMsgsCountRef.current &&
      last &&
      last.role === "assistant"
    ) {
      playCompletionCue();
    }
    prevMsgsCountRef.current = msgs.length;
  }, [msgs]);
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [practiceSeed, setPracticeSeed] = useState(0);
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
  const voiceEnabled = process.env.NEXT_PUBLIC_VOICE_ENABLED === "1";

  useEffect(() => {
    // Sprint 27: cookie auth.
    if (!topicId || Number.isNaN(topicId)) return;
    let cancelled = false;
    (async () => {
      try {
        const [me, loadedTopic, loadedFollowups] = await Promise.all([api.me(), api.topic(topicId), api.topicFollowups(topicId)]);
        if (cancelled) return;
        setUser(me);
        setTopic(loadedTopic);
        setFollowups(loadedFollowups);
      } catch (err: unknown) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          router.push("/login");
          return;
        }
        router.push("/subjects");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [topicId, router]);

  // Sprint 42: T1D recovery mode — fetch recommend-next для RecoveryBadge.
  // Показывается только если recovery_mode=true (т.е. была недавняя hypo/hyper).
  // Luna Pro safety: timing-based, НЕ glucose data.
  useEffect(() => {
    if (!topicId || Number.isNaN(topicId)) return;
    api
      .recommendNext()
      .then((data) => {
        setRecommendNext({
          recovery_mode: data.recovery_mode,
          recovery_reason: data.recovery_reason,
          minutes_since_pause: data.minutes_since_pause,
        });
      })
      .catch(() => {
        // Sprint 42: silent failure (не критично для UX)
        setRecommendNext(null);
      });
  }, [topicId]);

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
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs]);

  async function send(textOverride?: string) {
    const text = (textOverride ?? input).trim();
    if (!text || busy) return;
    setActionError(null);
    const next: ChatMsg[] = [...msgs, { role: "user", content: text }];
    setMsgs(next);
    setInput("");
    setBusy(true);

    try {
      const resp = await api.aiChat(next, topicId);
      setMsgs((m) => [...m, { role: "assistant", content: resp.content }]);
    } catch (err: unknown) {
      const message = extractErrorMessage(err);
      setActionError(message);
      setMsgs((m) => [
        ...m,
        {
          role: "assistant",
          content: message,
          error: message,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function explain() {
    if (busy) return;
    setActionError(null);
    setBusy(true);
    try {
      const r = await api.aiExplain(topicId);
      setMsgs((m) => [
        ...m,
        { role: "assistant", content: r.content, sources: r.sources },
      ]);
    } catch (err) {
      const message = extractErrorMessage(err);
      setActionError(message);
      // Sprint 12: T1D-friendly error UI (вместо текстовой inline-ошибки).
      setMsgs((m) => [
        ...m,
        {
          role: "assistant",
          content: message,
          error: message,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function generate(nextSeed?: number) {
    if (busy) return;
    const seed = nextSeed ?? practiceSeed;
    setActionError(null);
    setBusy(true);
    setExercise(null);
    setCheckResult(null);
    setUserAnswer("");
    try {
      // Pilot Core Stage 1 — secure flow: server-owned truth, opaque id.
      const r = await api.v2GenerateExercise({
        topic_id: topicId,
        // MVP rescue: use a small rotating explicit difficulty as variation seed.
        difficulty: (seed % 5) + 1,
      });
      setPracticeSeed(seed);
      setExercise({
        exercise_id: r.exercise_id,
        question_text: r.question_text,
        options: r.options,
        type: r.type,
        // correct_answer и explanation придут ПОСЛЕ submit (server-trusted).
      });
    } catch (err: unknown) {
      setActionError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function checkAnswer() {
    if (!exercise?.exercise_id) return;
    setActionError(null);
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
    } catch (err: unknown) {
      setActionError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="prism-shell min-h-dvh">
      <Header user={user} backHref="/subjects" backLabel="Все предметы" title={topic?.name || "Тема"} />

      <section
        onCopy={(event) => event.preventDefault()}
        onCut={(event) => event.preventDefault()}
        className="prism-lesson-grid select-none"
      >
        <aside className="prism-card pad prism-practice-column flex flex-col gap-3">
          <div className="prism-kicker">Lesson Cockpit</div>
          <h1 className="text-3xl font-black tracking-[-0.05em]">{topic?.name || "Тема"}</h1>
          <p className="text-sm text-[color:var(--prism-muted)]">Объяснение, практика и чат собраны как рабочая панель занятия.</p>

          <button
            type="button"
            onClick={explain}
            disabled={busy}
            className="prism-action primary w-full"
          >
            {busy && !exercise ? "AI думает…" : "Объяснить"}
          </button>
          <button
            type="button"
            onClick={() => {
              const nextSeed = practiceSeed + 1;
              setPracticeSeed(nextSeed);
              generate(nextSeed);
            }}
            disabled={busy}
            className="prism-action w-full"
          >
            Практика
          </button>

          {msgs.length > 0 && !showClearConfirm && (
            <button
              type="button"
              onClick={() => setShowClearConfirm(true)}
              aria-label="Очистить чат"
              className="prism-action w-full"
            >
              🧹 Очистить
            </button>
          )}
          {showClearConfirm && (
            <div className="rounded-3xl border border-amber-300/40 bg-amber-500/10 p-3 text-sm">
              <div className="font-black text-amber-700 dark:text-amber-200">Удалить всю историю?</div>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setMsgs([]);
                    setExercise(null);
                    setUserAnswer("");
                    setCheckResult(null);
                    setInput("");
                    setActionError(null);
                    localStorage.removeItem(draftKey(topicId));
                    api.topicDraftClear(topicId).catch(() => {});
                    setShowClearConfirm(false);
                  }}
                  className="prism-action primary"
                >
                  Да, удалить
                </button>
                <button type="button" onClick={() => setShowClearConfirm(false)} className="prism-action">Отмена</button>
              </div>
            </div>
          )}

          {actionError && (
            <div role="alert" className="rounded-3xl border border-red-400/30 bg-red-500/10 p-3 text-sm font-bold text-red-500">
              {actionError}
            </div>
          )}

          <div className="mt-auto space-y-3">
            <SessionTimer />
            <CGMStatus />
            <PauseButton
              onPause={(reason) => {
                api.sessionsPause(reason, Number(topicId)).catch((e) => {
                  console.error("Pause logging failed:", e);
                });
              }}
            />
          </div>
        </aside>

        <section className="prism-card pad prism-scroll prism-explain-column">
          <div className="prism-kicker">Learning Stage</div>
          {!exercise && msgs.length === 0 && (
            <div className="mt-8 grid place-items-center rounded-[32px] border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-8 text-center">
              <div className="prism-orb relative w-full max-w-[520px]" aria-hidden="true" />
              <h2 className="mt-6 text-3xl font-black tracking-[-0.05em]">Начни с объяснения или практики</h2>
              <p className="mt-2 max-w-lg text-sm text-[color:var(--prism-muted)]">Здесь появится учебный материал, проверка ответа и подсказки. Текстовые блоки остаются светлыми и читаемыми даже в тёмной теме.</p>
            </div>
          )}

          {exercise && (
            <section data-testid="exercise-card" className="lesson-readable mt-5 rounded-[30px] p-5 shadow-glow">
              <div className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Задание</div>
              <SafeMarkdown text={exercise.question_text} className="mt-2" />
              {exercise.options && exercise.options.length > 0 && (
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {exercise.options.map((opt) => (
                    <button
                      key={opt}
                      onClick={() => {
                        setUserAnswer(opt);
                        setCheckResult(null);
                        setActionError(null);
                      }}
                      className={`min-h-12 rounded-2xl border px-4 py-3 text-left text-sm font-bold ${
                        userAnswer === opt
                          ? "prism-option-button-active"
                          : "prism-option-button hover:border-[color:var(--prism-accent)]"
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              )}
              {(!exercise.options || exercise.options.length === 0 || exercise.type === "numeric" || exercise.type === "text") ? (
                <input
                  value={userAnswer}
                  onChange={(e) => {
                    setUserAnswer(e.target.value);
                    setCheckResult(null);
                    setActionError(null);
                  }}
                  placeholder={exercise.type === "numeric" ? "Числовой ответ" : "Текстовый ответ"}
                  className="prism-input mt-4"
                />
              ) : null}
              <button
                type="button"
                onClick={checkAnswer}
                disabled={busy || !userAnswer}
                className="prism-action primary mt-4"
              >
                Проверить
              </button>
              {checkResult && (
                <div className={`mt-4 rounded-3xl p-4 text-sm ${checkResult.is_correct ? "bg-emerald-100 text-emerald-950" : "bg-rose-100 text-rose-950"}`}>
                  <div className="font-black">{checkResult.is_correct ? "Верно!" : "Есть ошибка"} (оценка {Math.round(checkResult.score * 100)}%)</div>
                  {checkResult.first_error && <div className="mt-1">Шаг ошибки: {checkResult.first_error}</div>}
                  <SafeMarkdown text={checkResult.explanation} className="mt-2" />
                  {!checkResult.is_correct && checkResult.score < 0.6 && (
                    <div className="mt-3 rounded-2xl bg-[color:var(--prism-panel-solid)]/70 p-3 text-xs text-[color:var(--prism-ink)]">Попроси подсказку или попробуй ещё раз — репетитор поможет без раскрытия ответа.</div>
                  )}
                  {checkResult.is_correct && (
                    <button
                      type="button"
                      onClick={() => {
                        const nextSeed = practiceSeed + 1;
                        setPracticeSeed(nextSeed);
                        generate(nextSeed);
                      }}
                      disabled={busy}
                      className="prism-action mt-3"
                    >
                      Следующее задание
                    </button>
                  )}
                </div>
              )}
            </section>
          )}
        </section>

        <aside className="prism-card pad prism-chat-column flex min-h-[420px] flex-col">
          <div className="prism-kicker">Tutor Chat</div>
          <section ref={scrollRef} className="prism-chat-surface prism-scroll mt-4 flex-1 space-y-3 rounded-[28px] border border-[color:var(--prism-line)] p-3">
            {msgs.length === 0 && <p className="text-sm text-[color:var(--prism-muted)]">Напиши вопрос репетитору или нажми «Объяснить» / «Практика».</p>}
            {msgs.map((m, i) => {
              const isLastAssistant = i === msgs.length - 1 && m.role === "assistant";
              const followUps = isLastAssistant && !busy ? followups : [];
              return (
                <div
                  key={i}
                  data-testid={`chat-message-${m.role}`}
                  className={`max-w-[96%] overflow-hidden rounded-3xl px-4 py-3 text-sm shadow-sm ${m.role === "user" ? "ml-auto bg-[color:var(--prism-accent)] text-white" : "prism-chat-bubble-assistant mr-auto"}`}
                >
                  {m.role === "user" ? (
                    <span className="whitespace-pre-wrap break-words">{m.content}</span>
                  ) : (
                    <>
                      {m.sources && m.sources.length > 0 && (
                        <div className="mb-3 rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs">
                          <div className="mb-1 font-black text-amber-800">📖 Источник:</div>
                          <ul className="space-y-1">
                            {m.sources.map((s, idx) => (
                              <li key={idx} className="break-words text-amber-900">{s.label || `${s.material_title}${s.page_number != null ? `, стр. ${s.page_number}` : ""}`}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <SafeMarkdown text={m.content} className="break-words [&_*]:break-words [&_*]:max-w-full" />
                      {followUps.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {followUps.map((action) => (
                            <button key={action.label} type="button" onClick={() => send(action.prompt)} className="prism-pill" disabled={busy}>{action.label}</button>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
            {busy && <div className="prism-chat-bubble-assistant mr-auto rounded-3xl px-4 py-3 text-sm shadow-sm">AI думает…</div>}
          </section>

          <form onSubmit={(e) => { e.preventDefault(); send(); }} className="mt-3 pb-[env(safe-area-inset-bottom)]">
            <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Задай вопрос репетитору…"
                maxLength={500}
                aria-describedby="input-hint"
                className="prism-input"
                disabled={busy}
              />
              {voiceEnabled && <VoiceMicButton disabled={busy} onTranscript={(text) => setInput((prev) => (prev ? prev + " " : "") + text)} onError={(msg) => setActionError("Микрофон: " + msg)} />}
              <button type="submit" disabled={busy || !input.trim()} className="prism-action primary">{busy ? "⏳" : "Отправить"}</button>
            </div>
            <div id="input-hint" className="mt-2 flex items-center justify-between text-xs text-[color:var(--prism-muted)]">
              <span>Enter — отправить</span>
              <span className={input.length > 400 ? "font-black text-amber-600" : ""}>{input.length}/500</span>
            </div>
          </form>
        </aside>
      </section>
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