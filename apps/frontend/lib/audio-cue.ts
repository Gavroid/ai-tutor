"use client";

/**
 * Sprint 21: Audio cue helper — проигрывает короткий звук при завершении задачи.
 *
 * По дизайн-нотам (docs/future/T1D-support-notes.md):
 * "Audio cue on completion: для детей которые могут не смотреть на экран."
 *
 * Использует Web Audio API (не нужны аудио-файлы).
 * - Создаёт OscillatorNode с sine wave
 * - Три коротких beeps в стиле "ding-ding-ding" (achievement unlocked feel)
 * - 300ms длительность, 800Hz частота
 *
 * UX:
 * - opt-in (нужен user gesture для AudioContext)
 * - Громкость 0.1 (не громко, не раздражает)
 * - Отключаемо (respect prefers-reduced-motion)
 */

let audioContextSingleton: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (audioContextSingleton) return audioContextSingleton;

  try {
    // TypeScript не знает про webkit AudioContext — используем any.
    const Ctx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext })
        .webkitAudioContext;
    audioContextSingleton = new Ctx();
    return audioContextSingleton;
  } catch (e) {
    console.warn("AudioContext not supported:", e);
    return null;
  }
}

/**
 * Проигрывает "achievement" cue — три коротких beeps.
 * Требует user gesture для AudioContext.resume() (правило браузеров).
 */
export function playCompletionCue(): void {
  // Respect prefers-reduced-motion (WCAG 2.1).
  if (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  ) {
    return;
  }

  const ctx = getAudioContext();
  if (!ctx) return;

  // Браузер требует user gesture для audio — пытаемся resume.
  if (ctx.state === "suspended") {
    ctx.resume().catch(() => {
      // ignore — пользователь ещё не взаимодействовал
    });
  }

  const now = ctx.currentTime;
  const beepFreq = 800; // Hz — приятный "achievement" звук
  const beepDuration = 0.08; // 80ms — короткий
  const gap = 0.08; // пауза между beeps
  const volume = 0.1; // тихо, не агрессивно

  // 3 beeps с нарастающей высотой
  [0, 1, 2].forEach((i) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    osc.frequency.value = beepFreq + i * 100; // 800, 900, 1000 Hz
    gain.gain.value = 0;

    osc.connect(gain);
    gain.connect(ctx.destination);

    const startTime = now + i * (beepDuration + gap);
    const endTime = startTime + beepDuration;

    // Attack-decay envelope (плавное появление/затухание)
    gain.gain.setValueAtTime(0, startTime);
    gain.gain.linearRampToValueAtTime(volume, startTime + 0.01);
    gain.gain.setValueAtTime(volume, endTime - 0.02);
    gain.gain.linearRampToValueAtTime(0, endTime);

    osc.start(startTime);
    osc.stop(endTime + 0.01);
  });
}

/**
 * Хук для удобного использования в React-компонентах.
 * Возвращает функцию, которую можно вызвать по событию.
 */
export function useCompletionCue(): () => void {
  return playCompletionCue;
}