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
  const [activePane, setActivePane] = useState<"chat" | "lesson" | "practice">("chat");

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

  const paneButton = (pane: "chat" | "lesson" | "practice", label: string) => (
    <button
      type="button"
      onClick={() => setActivePane(pane)}
      className={`split-tab ${activePane === pane ? "split-tab-active" : ""}`}
    >
      {label}
    </button>
  );

  return (
    <main className="split-shell min-h-dvh">
      <Header user={user} backHref="/subjects" backLabel="Все предметы" title={topic?.name || "Тема"} />

      <nav className="split-mobile-tabs" aria-label="Разделы урока">
        {paneButton("chat", "Чат")}
        {paneButton("lesson", "Урок")}
        {paneButton("practice", "Практика")}
      </nav>

      <section
        onCopy={(event) => event.preventDefault()}
        onCut={(event) => event.preventDefault()}
        className="split-desktop-grid select-none"
      >
        <aside className={`split-panel split-lesson ${activePane === "lesson" ? "flex" : "hidden xl:flex"}`}>
          <div className="split-kicker">Урок</div>
          <h1 className="split-title">{topic?.name || "Тема"}</h1>
          <p className="split-muted">Сначала попроси объяснение, затем переходи к практике. Чат остаётся главным рабочим пространством.</p>

          <div className="split-actions">
            <button
              type="button"
              onClick={explain}
              disabled={busy}
              className="split-button split-button-primary"
            >
              {busy && !exercise ? "AI думает…" : "Объяснить"}
            </button>
            <button
              type="button"
              onClick={() => {
                const nextSeed = practiceSeed + 1;
                setPracticeSeed(nextSeed);
                generate(nextSeed);
                setActivePane("practice");
              }}
              className="split-button"
            >
              Практика
            </button>
            {msgs.length > 0 && !showClearConfirm && (
              <button
                type="button"
                onClick={() => setShowClearConfirm(true)}
                aria-label="Очистить чат"
                className="split-button"
              >
                🧹 Очистить
              </button>
            )}
          </div>

          {showClearConfirm && (
            <div className="split-callout warn">
              <div className="font-black">Удалить всю историю?</div>
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
                  className="split-button split-button-primary"
                >
                  Да, удалить
                </button>
                <button type="button" onClick={() => setShowClearConfirm(false)} className="split-button">Нет</button>
              </div>
            </div>
          )}

          {actionError && <div role="alert" className="split-callout danger">{actionError}</div>}

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

        <section className={`split-panel split-chat ${activePane === "chat" ? "flex" : "hidden xl:flex"}`}>
          <div className="split-kicker">Чат с репетитором</div>
          <section ref={scrollRef} className="split-chat-scroll">
            {msgs.length === 0 && (
              <div className="split-empty">
                <div className="split-orb" aria-hidden="true" />
                <h2>Спроси репетитора</h2>
                <p>Например: «Объясни среднее арифметическое проще» или нажми «Объяснить» в разделе урока.</p>
              </div>
            )}
            {msgs.map((m, i) => {
              const isLastAssistant = i === msgs.length - 1 && m.role === "assistant";
              const followUps = isLastAssistant && !busy ? followups : [];
              return (
                <div
                  key={i}
                  data-testid={`chat-message-${m.role}`}
                  className={`split-bubble ${m.role === "user" ? "split-bubble-user" : "split-bubble-assistant"}`}
                >
                  {m.role === "user" ? (
                    <span className="whitespace-pre-wrap break-words">{m.content}</span>
                  ) : (
                    <>
                      {m.sources && m.sources.length > 0 && (
                        <div className="split-source">
                          <div className="font-black">Источник</div>
                          <ul className="mt-1 space-y-1">
                            {m.sources.map((source, idx) => (
                              <li key={idx}>{source.label || `${source.material_title}${source.page_number != null ? `, стр. ${source.page_number}` : ""}`}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <SafeMarkdown text={m.content} className="split-markdown" />
                      {followUps.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {followUps.map((action) => (
                            <button key={action.label} type="button" onClick={() => send(action.prompt)} className="split-chip" disabled={busy}>{action.label}</button>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
            {busy && <div className="split-bubble split-bubble-assistant">AI думает…</div>}
          </section>

          <form onSubmit={(event) => { event.preventDefault(); send(); }} className="split-chat-form">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Задай вопрос репетитору…"
              maxLength={500}
              aria-describedby="input-hint"
              className="split-input"
              disabled={busy}
            />
            {voiceEnabled && <VoiceMicButton disabled={busy} onTranscript={(text) => setInput((prev) => (prev ? prev + " " : "") + text)} onError={(msg) => setActionError("Микрофон: " + msg)} />}
            <button type="submit" disabled={busy || !input.trim()} className="split-send">{busy ? "⏳" : "Отправить"}</button>
          </form>
          <div id="input-hint" className="split-hint"><span>Enter — отправить</span><span>{input.length}/500</span></div>
        </section>

        <aside className={`split-panel split-practice ${activePane === "practice" ? "block" : "hidden xl:block"}`}>
          <div className="split-kicker">Практика</div>
          {!exercise && (
            <div className="split-empty compact">
              <h2>Практика появится здесь</h2>
              <p>Нажми «Практика» в разделе урока, чтобы получить новое задание.</p>
            </div>
          )}
          {exercise && (
            <section data-testid="exercise-card" className="split-task-card">
              <div className="split-kicker green">Задание</div>
              <SafeMarkdown text={exercise.question_text} className="split-task-text" />
              {exercise.options && exercise.options.length > 0 && (
                <div className="mt-4 grid gap-2">
                  {exercise.options.map((opt) => (
                    <button
                      key={opt}
                      onClick={() => {
                        setUserAnswer(opt);
                        setCheckResult(null);
                        setActionError(null);
                      }}
                      className={`split-answer ${userAnswer === opt ? "active" : ""}`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              )}
              {(!exercise.options || exercise.options.length === 0 || exercise.type === "numeric" || exercise.type === "text") ? (
                <input
                  value={userAnswer}
                  onChange={(event) => {
                    setUserAnswer(event.target.value);
                    setCheckResult(null);
                    setActionError(null);
                  }}
                  placeholder={exercise.type === "numeric" ? "Числовой ответ" : "Текстовый ответ"}
                  className="split-input mt-4"
                />
              ) : null}
              <button
                type="button"
                onClick={checkAnswer}
                disabled={busy || !userAnswer}
                className="split-button split-button-primary mt-4 w-full"
              >
                Проверить
              </button>
              {checkResult && (
                <div className={`split-result ${checkResult.is_correct ? "ok" : "bad"}`}>
                  <div className="font-black">{checkResult.is_correct ? "Верно!" : "Есть ошибка"} ({Math.round(checkResult.score * 100)}%)</div>
                  {checkResult.first_error && <div className="mt-1">Шаг ошибки: {checkResult.first_error}</div>}
                  <SafeMarkdown text={checkResult.explanation} className="mt-2" />
                  {!checkResult.is_correct && checkResult.score < 0.6 && <div className="mt-3 rounded-2xl bg-white/10 p-3 text-xs">Попробуй ещё раз — репетитор поможет без раскрытия ответа.</div>}
                  {checkResult.is_correct && (
                    <button
                      type="button"
                      onClick={() => {
                        const nextSeed = practiceSeed + 1;
                        setPracticeSeed(nextSeed);
                        generate(nextSeed);
                      }}
                      disabled={busy}
                      className="split-button mt-3 w-full"
                    >
                      Следующее задание
                    </button>
                  )}
                </div>
              )}
            </section>
          )}
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