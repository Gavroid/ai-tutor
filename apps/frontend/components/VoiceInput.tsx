"use client";

import { useEffect, useRef, useState } from "react";

interface VoiceInputProps {
  /** Sprint 6.2 MVP: вызывается когда recording распознан.
   *  В MVP версии передаём raw text из placeholder (transcribe mock).
   *  В будущем — реальный Whisper API через backend. */
  onTranscript: (text: string) => void;
  /** Disabled state (например, во время отправки). */
  disabled?: boolean;
}

/**
 * Sprint 6.2 MVP — кнопка микрофона для голосового ввода.
 *
 * TODO Sprint 6.2+: реальное распознавание через:
 * - MediaRecorder API в браузере
 * - POST /api/v1/voice/transcribe (Whisper или MiniMax ASR)
 * - Возврат text → onTranscript(text)
 *
 * Сейчас: UI кнопка + disabled state + placeholder transcript
 * (для проверки UX без интеграции с ASR).
 */
export default function VoiceInput({ onTranscript, disabled }: VoiceInputProps) {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      if (recorderRef.current && recorderRef.current.state === "recording") {
        recorderRef.current.stop();
      }
    };
  }, []);

  async function start() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        try {
          // Sprint 6.2 TODO: POST /api/v1/voice/transcribe
          // Сейчас отправляем raw blob в handler (mock) — пусть пользователь наберёт.
          console.log("voice recorded:", blob.size, "bytes");
          // MVP placeholder: отправляем короткий текст, чтобы пользователь увидел flow.
          onTranscript("[голосовое сообщение — пока не распознаётся]");
        } catch (e) {
          setError("Не удалось распознать речь");
        }
      };

      recorder.start();
      setRecording(true);
    } catch (e: unknown) {
      const err = e as { name?: string; message?: string };
      if (err?.name === "NotAllowedError") {
        setError("Нет доступа к микрофону. Разрешите в настройках браузера.");
      } else {
        setError("Микрофон не поддерживается: " + (err?.message ?? "неизвестная ошибка"));
      }
    }
  }

  function stop() {
    if (recorderRef.current && recorderRef.current.state === "recording") {
      recorderRef.current.stop();
      setRecording(false);
    }
  }

  return (
    <div className="inline-flex flex-col items-end gap-1">
      <button
        type="button"
        disabled={disabled}
        onClick={recording ? stop : start}
        data-testid="voice-input-button"
        aria-label={recording ? "Остановить запись" : "Записать голос"}
        className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-medium transition disabled:opacity-50 ${
          recording
            ? "bg-rose-500 text-white animate-pulse hover:bg-rose-600"
            : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
        }`}
      >
        {recording ? "⏹" : "🎤"}
      </button>
      {error && (
        <span className="max-w-[200px] text-right text-[10px] text-rose-600">{error}</span>
      )}
    </div>
  );
}