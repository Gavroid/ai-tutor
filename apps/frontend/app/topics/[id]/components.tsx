"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import SafeMarkdown from "@/components/SafeMarkdown";
import PauseButton from "@/components/PauseButton";
import SessionTimer from "@/components/SessionTimer";
import CGMStatus from "@/components/CGMStatus";
import { api } from "@/lib/api";
import type { ChatMsg, TopicFollowup } from "@/types";

export type LessonPane = "chat" | "lesson" | "practice";

export type Exercise = {
  exercise_id: number;
  question_text: string;
  options: string[] | null;
  type: string;
  correct_answer?: string;
  explanation?: string;
};

type CheckResult = {
  is_correct: boolean;
  score: number;
  first_error: string | null;
  explanation: string;
  hint_level: number;
  error_type?: string | null;
} | null;

export function MobileLessonTabs({
  activePane,
  onPaneChange,
}: {
  activePane: LessonPane;
  onPaneChange: (pane: LessonPane) => void;
}) {
  const paneButton = (pane: LessonPane, label: string) => (
    <button
      type="button"
      onClick={() => onPaneChange(pane)}
      className={`split-tab ${activePane === pane ? "split-tab-active" : ""}`}
    >
      {label}
    </button>
  );

  return (
    <nav className="split-mobile-tabs" aria-label="Разделы урока">
      {paneButton("chat", "Чат")}
      {paneButton("lesson", "Урок")}
      {paneButton("practice", "Практика")}
    </nav>
  );
}

export function LessonRail({
  activePane,
  busy,
  hasExercise,
  hasMessages,
  showClearConfirm,
  actionError,
  timerMinutes,
  onExplain,
  onGeneratePractice,
  onShowClearConfirm,
  onCancelClear,
  onConfirmClear,
  nextStep,
  nextTopicId,
  onPause,
  onGoToPractice,
  onRetryPractice,
  onNextTask,
  onNextTopic,
}: {
  activePane: LessonPane;
  busy: boolean;
  hasExercise: boolean;
  hasMessages: boolean;
  showClearConfirm: boolean;
  actionError: string | null;
  timerMinutes: number;
  onExplain: () => void;
  onGeneratePractice: () => void;
  onShowClearConfirm: () => void;
  onCancelClear: () => void;
  onConfirmClear: () => void;
  nextStep: { title: string; body: string; tone: "focus" | "practice" | "review"; action: "explain" | "practice" | "retry" | "next_task" | "next_topic" };
  nextTopicId: number | null;
  onPause: (reason: "hypo" | "hyper" | "break" | "other") => void;
  onGoToPractice: () => void;
  onRetryPractice: () => void;
  onNextTask: () => void;
  onNextTopic: () => void;
}) {
  const primaryAction = (() => {
    if (nextStep.action === "next_topic" && nextTopicId) {
      return { label: "Следующая тема", onClick: onNextTopic, disabled: busy };
    }
    if (nextStep.action === "next_task") {
      return { label: "Следующее задание", onClick: onNextTask, disabled: busy };
    }
    if (nextStep.action === "retry") {
      return { label: "Попробовать ещё раз", onClick: onRetryPractice, disabled: busy || !hasExercise };
    }
    if (nextStep.action === "practice") {
      return { label: "Перейти к практике", onClick: onGoToPractice, disabled: busy };
    }
    return { label: "Начать объяснение", onClick: onExplain, disabled: busy };
  })();

  return (
    <aside className={`split-panel split-lesson ${activePane === "lesson" ? "flex" : "hidden xl:flex"}`}>
      <div className="split-kicker">Урок</div>
      <div className="split-lesson-note">
        <p>Сначала попроси объяснение, затем переходи к практике. Чат остаётся главным рабочим пространством.</p>
      </div>

      <div className="split-actions">
        <button type="button" onClick={onExplain} disabled={busy} className="split-button split-button-primary">
          {busy && !hasExercise ? "AI думает…" : "Объяснить"}
        </button>
        <button type="button" onClick={onGeneratePractice} className="split-button">
          Практика
        </button>
        {hasMessages && !showClearConfirm && (
          <button type="button" onClick={onShowClearConfirm} aria-label="Очистить чат" className="split-button">
            🧹 Очистить
          </button>
        )}
      </div>

      {showClearConfirm && (
        <div className="split-callout warn">
          <div className="font-black">Удалить всю историю?</div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <button type="button" onClick={onConfirmClear} aria-label="Да, удалить" className="split-button split-button-primary">
              Да
            </button>
            <button type="button" onClick={onCancelClear} className="split-button">Нет</button>
          </div>
        </div>
      )}

      {actionError && <div role="alert" className="split-callout danger">{actionError}</div>}

      <div className={`split-callout ${nextStep.tone === "review" ? "warn" : ""}`}>
        <div className="split-kicker">Следующий шаг</div>
        <div className="mt-2 text-base font-black text-[color:var(--split-ink)]">{nextStep.title}</div>
        <p className="mt-1 text-xs leading-5 text-[color:var(--split-muted)]">{nextStep.body}</p>
        <button type="button" onClick={primaryAction.onClick} disabled={primaryAction.disabled} className="split-button split-button-primary mt-3 w-full">
          {primaryAction.label}
        </button>
        {nextStep.action === "next_topic" && !nextTopicId && (
          <p className="mt-2 text-xs text-[color:var(--split-muted)]">Маршрут завершён — можно закрепить тему ещё одним заданием.</p>
        )}
      </div>

      <div className="mt-auto space-y-3">
        <SessionTimer initialMinutesElapsed={timerMinutes} />
        <CGMStatus />
        <PauseButton onPause={onPause} />
      </div>
    </aside>
  );
}

export function TutorChat({
  activePane,
  scrollRef,
  messages,
  busy,
  followups,
  input,
  voiceEnabled,
  onInputChange,
  onSend,
  onVoiceError,
}: {
  activePane: LessonPane;
  scrollRef: RefObject<HTMLDivElement | null>;
  messages: ChatMsg[];
  busy: boolean;
  followups: TopicFollowup[];
  input: string;
  voiceEnabled: boolean;
  onInputChange: (value: string) => void;
  onSend: (textOverride?: string) => void;
  onVoiceError: (message: string) => void;
}) {
  return (
    <section className={`split-panel split-chat ${activePane === "chat" ? "flex" : "hidden xl:flex"}`}>
      <div className="split-kicker">Чат с репетитором</div>
      <section
        ref={scrollRef}
        className="split-chat-scroll"
        role="log"
        aria-live="polite"
        aria-label="Чат с репетитором — сообщения появляются здесь"
        aria-busy={busy}
      >
        {messages.length === 0 && (
          <div className="split-empty">
            <div className="split-orb compact" aria-hidden="true" />
            <h2>Спроси репетитора</h2>
            <p>Например: «Объясни среднее арифметическое проще» или нажми «Объяснить» в разделе урока.</p>
          </div>
        )}
        {messages.map((message, index) => {
          const isLastAssistant = index === messages.length - 1 && message.role === "assistant";
          const visibleFollowups = isLastAssistant && !busy ? followups : [];
          return (
            <div
              key={index}
              data-testid={`chat-message-${message.role}`}
              className={`split-bubble ${message.role === "user" ? "split-bubble-user" : "split-bubble-assistant"}`}
            >
              {message.role === "user" ? (
                <span className="whitespace-pre-wrap break-words">{message.content}</span>
              ) : (
                <>
                  {message.sources && message.sources.length > 0 && (
                    <div className="split-source">
                      <div className="font-black">Источник</div>
                      <ul className="mt-1 space-y-1">
                        {message.sources.map((source, idx) => (
                          <li key={idx}>{source.label || `${source.material_title}${source.page_number != null ? `, стр. ${source.page_number}` : ""}`}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <SafeMarkdown text={message.content} className="split-markdown" />
                  {visibleFollowups.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {visibleFollowups.map((action) => (
                        <button key={action.label} type="button" onClick={() => onSend(action.prompt)} className="split-chip" disabled={busy}>{action.label}</button>
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

      <form onSubmit={(event) => { event.preventDefault(); onSend(); }} className="split-chat-form">
        <div className={`split-composer-row ${voiceEnabled ? "has-voice" : ""}`}>
          <input
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            placeholder="Задай вопрос репетитору…"
            maxLength={500}
            // Sprint U2.1 (2026-08-23): aria-label для screen readers.
            // placeholder виден зрячим пользователям, но screen reader
            // его не объявляет как label. Добавляем явный.
            aria-label="Поле ввода вопроса репетитору"
            aria-describedby="input-hint"
            className="split-input"
            disabled={busy}
          />
          {voiceEnabled && <VoiceMicButton disabled={busy} onTranscript={(text) => onInputChange(input ? `${input} ${text}` : text)} onError={onVoiceError} />}
          <button type="submit" disabled={busy || !input.trim()} className="split-send">{busy ? "⏳" : "Отправить"}</button>
        </div>
      </form>
      <div id="input-hint" className="split-hint"><span>Enter — отправить</span><span>{input.length}/500</span></div>
    </section>
  );
}

export function PracticePanel({
  activePane,
  exercise,
  userAnswer,
  checkResult,
  busy,
  practiceSeed,
  onUserAnswerChange,
  onCheckAnswer,
  onGenerateNext,
}: {
  activePane: LessonPane;
  exercise: Exercise | null;
  userAnswer: string;
  checkResult: CheckResult;
  busy: boolean;
  practiceSeed: number;
  onUserAnswerChange: (answer: string) => void;
  onCheckAnswer: () => void;
  onGenerateNext: (nextSeed: number) => void;
}) {
  return (
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
              {exercise.options.map((option) => (
                <button key={option} onClick={() => onUserAnswerChange(option)} className={`split-answer ${userAnswer === option ? "active" : ""}`}>
                  {option}
                </button>
              ))}
            </div>
          )}
          {(!exercise.options || exercise.options.length === 0 || exercise.type === "numeric" || exercise.type === "text") ? (
            <input
              value={userAnswer}
              onChange={(event) => onUserAnswerChange(event.target.value)}
              placeholder={exercise.type === "numeric" ? "Числовой ответ" : "Текстовый ответ"}
              className="split-input mt-4"
            />
          ) : null}
          <button type="button" onClick={onCheckAnswer} disabled={busy || !userAnswer} className="split-button split-button-primary mt-4 w-full">
            Проверить
          </button>
          {checkResult && (
            <div className={`split-result ${checkResult.is_correct ? "ok" : "bad"}`}>
              <div className="font-black">{checkResult.is_correct ? "Верно!" : "Есть ошибка"} ({Math.round(checkResult.score * 100)}%)</div>
              {checkResult.first_error && <div className="mt-1">Шаг ошибки: {checkResult.first_error}</div>}
              <SafeMarkdown text={checkResult.explanation} className="mt-2" />
              {!checkResult.is_correct && checkResult.score < 0.6 && <div className="mt-3 rounded-2xl bg-white/10 p-3 text-xs">Попробуй ещё раз — репетитор поможет без раскрытия ответа.</div>}
              {checkResult.is_correct && (
                <button type="button" onClick={() => onGenerateNext(practiceSeed + 1)} disabled={busy} className="split-button mt-3 w-full">
                  Следующее задание
                </button>
              )}
            </div>
          )}
        </section>
      )}
    </aside>
  );
}

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
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        try {
          const response = await api.voiceTranscribe(blob);
          if (response.text?.trim()) onTranscript(response.text.trim());
          else onError("Не удалось распознать речь");
        } catch (error: unknown) {
          onError((error as Error)?.message || "Ошибка распознавания");
        }
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
      setSeconds(0);
      timerRef.current = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    } catch (error: unknown) {
      const msg = (error as Error)?.message?.includes("Permission") ? "Нет доступа к микрофону" : "Микрофон недоступен";
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

  useEffect(
    () => () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        try {
          recorder.stop();
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
      title={typeof navigator !== "undefined" && !navigator.mediaDevices ? "Микрофон не поддерживается" : recording ? `Идёт запись… ${seconds}с` : "Записать голос"}
      className={`relative h-11 w-11 shrink-0 rounded-full text-2xl transition ${recording ? "animate-pulse bg-rose-500 text-white shadow-lg shadow-rose-500/40" : "bg-slate-100 text-[color:var(--prism-muted)] hover:bg-slate-200"} disabled:opacity-50`}
    >
      {recording ? "⏹" : "🎤"}
      {recording && <span className="absolute -right-2 -top-1 rounded bg-rose-700 px-1 text-[10px] font-semibold text-white">{seconds}s</span>}
    </button>
  );
}
