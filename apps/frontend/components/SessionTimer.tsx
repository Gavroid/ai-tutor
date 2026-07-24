"use client";

/**
 * Sprint 34: SessionTimer с эскалацией предупреждений.
 *
 * T1D safety design (Luna Pro):
 * - НЕ интерпретирует glucose data.
 * - НЕ отправляет данные в Telegram автоматически.
 * - Использует ТОЛЬКО timing-based эскалацию.
 *
 * Уровни (escalation tiers):
 * - 20 мин: мягкий warning (☕ "сделай перерыв")
 * - 40 мин: настойчивый warning (🌿 "попей воды / перекуси")
 * - 60 мин: явный warning (🛑 "отдохни, streak не сломается")
 *
 * UX:
 * - НЕ блокирует, НЕ давит
 * - 48px кнопки (T1D моторика)
 * - "Спасибо, я заметил" — без слежения
 * - aria-live="polite" — screen readers
 * - Каждый уровень dismiss отдельно (или cumulative через allDismissed)
 *
 * Sprint 34 NOTE: ВСЕ данные timing-based. Не используем CGM/Nightscout.
 */

import { useEffect, useState } from "react";

interface SessionTimerProps {
  /** Optional callback при показе warning любого уровня. */
  onWarn?: (level: 1 | 2 | 3, minutes: number) => void;
  /** Запомнить dismissed level (default true). */
  persistDismissal?: boolean;
}

type WarningLevel = 0 | 1 | 2 | 3;

interface WarningTier {
  /** Через сколько минут показывать (от начала сессии). */
  thresholdMinutes: number;
  /** Цвет (T1D-friendly, без агрессии). */
  color: "amber" | "lime" | "rose";
  /** Эмодзи (decorative, aria-hidden). */
  emoji: string;
  /** Заголовок. */
  title: (m: number) => string;
  /** Описание (calming, не давление). */
  description: string;
  /** Primary button text. */
  primary: string;
}

const TIERS: WarningTier[] = [
  // Tier 0 (no warning) — пропускаем в индексации
  {
    thresholdMinutes: 0,
    color: "amber",
    emoji: "",
    title: () => "",
    description: "",
    primary: "",
  },
  {
    // Tier 1: 20 мин
    thresholdMinutes: 20,
    color: "amber",
    emoji: "☕",
    title: (m) => `Ты занимаешься уже ${m} минут`,
    description:
      "Не забывай делать перерывы. Можешь отдохнуть, попить воды или перекусить. Твоя сессия сохранится.",
    primary: "Спасибо, я заметил",
  },
  {
    // Tier 2: 40 мин
    thresholdMinutes: 40,
    color: "lime",
    emoji: "🌿",
    title: (m) => `${m} минут — это уже долго`,
    description:
      "Мозг устаёт после 40 минут. Попей воды, разомнись, или выйди на свежий воздух. Streak не прервётся.",
    primary: "Я отдохну",
  },
  {
    // Tier 3: 60 мин
    thresholdMinutes: 60,
    color: "rose",
    emoji: "🛑",
    title: (m) => `Ты занимаешься больше часа (${m} мин)`,
    description:
      "Серьёзно, сделай перерыв. Учёба лучше усваивается после отдыха. Streak не сломается, а ты сохранишь силы.",
    primary: "Я сделаю перерыв",
  },
];

const COLOR_CLASSES: Record<WarningTier["color"], string> = {
  amber: "border-amber-200 bg-amber-50 text-amber-900",
  lime: "border-lime-200 bg-lime-50 text-lime-900",
  rose: "border-rose-200 bg-rose-50 text-rose-900",
};

const BUTTON_CLASSES: Record<WarningTier["color"], string> = {
  amber: "bg-amber-600 hover:bg-amber-700 focus-visible:ring-amber-500",
  lime: "bg-lime-600 hover:bg-lime-700 focus-visible:ring-lime-500",
  rose: "bg-rose-600 hover:bg-rose-700 focus-visible:ring-rose-500",
};

const BUTTON_SECONDARY: Record<WarningTier["color"], string> = {
  amber: "border-amber-200 text-amber-700 hover:bg-amber-50",
  lime: "border-lime-200 text-lime-700 hover:bg-lime-50",
  rose: "border-rose-200 text-rose-700 hover:bg-rose-50",
};

export default function SessionTimer({
  onWarn,
  persistDismissal = true,
}: SessionTimerProps) {
  const [minutesElapsed, setMinutesElapsed] = useState(0);
  const [dismissedLevel, setDismissedLevel] = useState<WarningLevel>(0);

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = (Date.now() - startTime) / 60000;
      setMinutesElapsed(elapsed);
    }, 60000); // обновляем каждую минуту
    return () => clearInterval(interval);
  }, []);

  // Определяем текущий уровень (какой tier активен)
  const currentLevel: WarningLevel = (() => {
    if (minutesElapsed >= TIERS[3].thresholdMinutes) return 3;
    if (minutesElapsed >= TIERS[2].thresholdMinutes) return 2;
    if (minutesElapsed >= TIERS[1].thresholdMinutes) return 1;
    return 0;
  })();

  // Показываем ТОЛЬКО если level > dismissedLevel
  const activeLevel: WarningLevel =
    currentLevel > dismissedLevel ? currentLevel : 0;

  useEffect(() => {
    if (activeLevel > 0) {
      onWarn?.(activeLevel as 1 | 2 | 3, Math.floor(minutesElapsed));
    }
  }, [activeLevel, minutesElapsed, onWarn]);

  if (activeLevel === 0) return null;

  const tier = TIERS[activeLevel];
  const colors = COLOR_CLASSES[tier.color];
  const buttonClasses = BUTTON_CLASSES[tier.color];
  const buttonSecondary = BUTTON_SECONDARY[tier.color];

  function handleDismiss() {
    if (persistDismissal) {
      setDismissedLevel(activeLevel);
    }
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={`rounded-2xl border-2 p-4 mb-4 ${colors}`}
      data-warning-level={activeLevel}
    >
      <div className="flex items-start gap-3">
        <div className="text-2xl flex-shrink-0" aria-hidden="true">
          {tier.emoji}
        </div>
        <div className="flex-1">
          <p className="font-medium mb-1">
            {tier.title(Math.floor(minutesElapsed))}
          </p>
          <p className="text-sm mb-3 leading-relaxed opacity-90">
            {tier.description}
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <button
              onClick={handleDismiss}
              className={`min-h-[48px] px-4 py-2 text-white rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-3 ${buttonClasses}`}
            >
              {tier.primary}
            </button>
            <button
              onClick={handleDismiss}
              className={`min-h-[48px] px-4 py-2 bg-white rounded-lg border text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-3 ${buttonSecondary}`}
            >
              Продолжить
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}