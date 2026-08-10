"use client";

import { useState } from "react";

type PauseReason = "break" | "hypo" | "hyper" | "other";

interface PauseButtonProps {
  onPause?: (reason: PauseReason) => void;
  enabled?: boolean;
}

const BREAKS = [
  { minutes: 5, label: "5 минут", note: "Коротко отвлечься" },
  { minutes: 15, label: "15 минут", note: "Нормальный перерыв" },
  { minutes: 30, label: "30 минут", note: "Вернуться позже" },
] as const;

export default function PauseButton({ onPause, enabled = true }: PauseButtonProps) {
  const [pausedFor, setPausedFor] = useState<number | null>(null);
  const [showOptions, setShowOptions] = useState(false);

  if (!enabled) return null;

  if (pausedFor) {
    return (
      <div role="status" aria-live="polite" className="split-pause-panel">
        <div className="split-kicker">Пауза</div>
        <div className="mt-3 text-lg font-black text-[color:var(--split-ink)]">Сессия сохранена</div>
        <p className="mt-1 text-xs leading-5 text-[color:var(--split-muted)]">Перерыв на {pausedFor} минут. Streak не сломается, продолжишь с этого места.</p>
        <button onClick={() => setPausedFor(null)} className="split-button split-button-primary mt-4 w-full">Я вернулся</button>
      </div>
    );
  }

  if (showOptions) {
    return (
      <div role="dialog" aria-labelledby="pause-title" className="split-pause-panel">
        <div id="pause-title" className="split-kicker">Сделать паузу</div>
        <p className="mt-3 text-xs leading-5 text-[color:var(--split-muted)]">Выбери длительность. Урок и чат сохранятся.</p>
        <div className="mt-4 grid gap-2">
          {BREAKS.map((item) => (
            <button
              key={item.minutes}
              type="button"
              onClick={() => {
                onPause?.("break");
                setPausedFor(item.minutes);
                setShowOptions(false);
              }}
              className="split-button split-pause-option"
            >
              <span className="font-black">{item.label}</span>
              <span>{item.note}</span>
            </button>
          ))}
        </div>
        <button type="button" onClick={() => setShowOptions(false)} className="split-button mt-3 w-full">Отмена</button>
      </div>
    );
  }

  return (
    <button onClick={() => setShowOptions(true)} className="split-button w-full" aria-label="Сделать паузу в занятии">
      Ⅱ Сделать паузу
    </button>
  );
}
