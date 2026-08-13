"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { api, getToken, ApiError } from "@/lib/api";
import Header from "@/components/Header";
import { playCompletionCue } from "@/lib/audio-cue";
import type { Topic, TopicFollowup, ChatMsg, User } from "@/types";
import { LessonRail, MobileLessonTabs, PracticePanel, TutorChat, type Exercise } from "./components";

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
  const searchParams = useSearchParams();
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

  const nextStep = (() => {
    if (checkResult?.is_correct) {
      return { title: "Закрепи навык", body: "Ответ верный. Возьми следующее задание или коротко объясни правило своими словами.", tone: "practice" as const };
    }
    if (checkResult && !checkResult.is_correct) {
      return { title: "Разбери ошибку", body: "Посмотри объяснение ошибки, исправь ответ и только потом бери новое задание.", tone: "review" as const };
    }
    if (exercise) {
      return { title: "Реши практику", body: "Сначала выбери или введи ответ, затем нажми “Проверить”.", tone: "practice" as const };
    }
    if (msgs.some((message) => message.role === "assistant")) {
      return { title: "Переходи к практике", body: "Объяснение уже есть. Нажми “Практика”, чтобы проверить понимание на задаче.", tone: "practice" as const };
    }
    return { title: "Начни с объяснения", body: "Нажми “Объяснить”: репетитор даст правило, пример и вопрос для самопроверки.", tone: "focus" as const };
  })();

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
    setActivePane("chat");
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

  return (
    <main className="split-shell min-h-dvh">
      <Header user={user} backHref="/subjects" backLabel="Все предметы" title={topic?.name || "Тема"} />

      <MobileLessonTabs activePane={activePane} onPaneChange={setActivePane} />

      <section
        onCopy={(event) => event.preventDefault()}
        onCut={(event) => event.preventDefault()}
        className="split-desktop-grid select-none"
      >
        <LessonRail
          activePane={activePane}
          busy={busy}
          hasExercise={Boolean(exercise)}
          hasMessages={msgs.length > 0}
          showClearConfirm={showClearConfirm}
          actionError={actionError}
          timerMinutes={process.env.NODE_ENV !== "production" ? Number(searchParams.get("timerMinutes") || 0) : 0}
          nextStep={nextStep}
          onExplain={explain}
          onGeneratePractice={() => {
            const nextSeed = practiceSeed + 1;
            setPracticeSeed(nextSeed);
            generate(nextSeed);
            setActivePane("practice");
          }}
          onShowClearConfirm={() => setShowClearConfirm(true)}
          onCancelClear={() => setShowClearConfirm(false)}
          onConfirmClear={() => {
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
          onPause={(reason) => {
            api.sessionsPause(reason, Number(topicId)).catch((e) => {
              console.error("Pause logging failed:", e);
            });
          }}
        />

        <TutorChat
          activePane={activePane}
          scrollRef={scrollRef}
          messages={msgs}
          busy={busy}
          followups={followups}
          input={input}
          voiceEnabled={voiceEnabled}
          onInputChange={setInput}
          onSend={send}
          onVoiceError={(msg) => setActionError("Микрофон: " + msg)}
        />

        <PracticePanel
          activePane={activePane}
          exercise={exercise}
          userAnswer={userAnswer}
          checkResult={checkResult}
          busy={busy}
          practiceSeed={practiceSeed}
          onUserAnswerChange={(answer) => {
            setUserAnswer(answer);
            setCheckResult(null);
            setActionError(null);
          }}
          onCheckAnswer={checkAnswer}
          onGenerateNext={(nextSeed) => {
            setPracticeSeed(nextSeed);
            generate(nextSeed);
          }}
        />
      </section>
    </main>
  );
}
