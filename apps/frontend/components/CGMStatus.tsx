"use client";

/**
 * Sprint 40: CGMStatus — T1D-friendly glucose badge.
 *
 * Luna Pro safety:
 * - НЕ интерпретирует glucose data (не говорит "высокий/низкий").
 * - ТОЛЬКО display (number + direction arrow).
 * - opt-in: показывает только если user enabled CGM.
 * - Без алертов и рекомендаций.
 *
 * UX:
 * - Calm colors (sky/blue — T1D-friendly).
 * - Trend arrow + last value.
 * - "Нет данных" placeholder если opt-out.
 * - aria-live="polite" (не агрессивный).
 */

import { useEffect, useState } from "react";

interface CGMStatusProps {
  /** Auto-refresh interval в ms (default 60 сек). */
  refreshIntervalMs?: number;
}

interface CGMLatestResponse {
  reading: {
    sgv: number;
    direction: string;
    date: number;
    date_string: string;
  };
  units: string;
  fetched_at: string;
}

interface CGMConfigResponse {
  nightscout_url: string;
  enabled: boolean;
}

const DIRECTION_ARROWS: Record<string, string> = {
  DoubleUp: "⇈",
  SingleUp: "↑",
  FortyFiveUp: "↗",
  Flat: "→",
  FortyFiveDown: "↘",
  SingleDown: "↓",
  DoubleDown: "⇊",
  NOT_COMPUTABLE: "?",
  RATE_OUT_OF_RANGE: "⚠",
};

export default function CGMStatus({ refreshIntervalMs = 60000 }: CGMStatusProps) {
  const [config, setConfig] = useState<CGMConfigResponse | null>(null);
  const [latest, setLatest] = useState<CGMLatestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    async function fetchConfig() {
      try {
        const r = await fetch("/api/v1/cgm/config", { credentials: "include" });
        if (!mounted) return;
        if (r.status === 401) {
          // Sprint 40: не залогинен — скрыть badge
          setConfig(null);
          setLoading(false);
          return;
        }
        if (r.ok) {
          const data = await r.json();
          setConfig(data);
        }
      } catch (e) {
        // Sprint 40: silent failure (не критично для UX)
        if (mounted) setError("config fetch failed");
      } finally {
        if (mounted) setLoading(false);
      }
    }

    async function fetchLatest() {
      if (!config?.enabled) return;
      try {
        const r = await fetch("/api/v1/cgm/latest", { credentials: "include" });
        if (!mounted) return;
        if (r.ok) {
          const data: CGMLatestResponse = await r.json();
          setLatest(data);
        } else if (r.status === 403) {
          setLatest(null);
        }
      } catch (e) {
        if (mounted) setLatest(null);
      }
    }

    async function tick() {
      await fetchConfig();
      await fetchLatest();
      if (mounted) {
        timeoutId = setTimeout(tick, refreshIntervalMs);
      }
    }

    tick();

    return () => {
      mounted = false;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [refreshIntervalMs, config?.enabled]);

  if (loading) return null;
  if (error) return null;
  if (!config?.enabled) return null;
  if (!latest) return null;

  const arrow = DIRECTION_ARROWS[latest.reading.direction] ?? "·";
  const time = new Date(latest.reading.date).toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      role="status"
      aria-live="polite"
      className="rounded-2xl border border-sky-200 bg-sky-50 p-3 mb-4 flex items-center gap-3"
      data-testid="cgm-status"
    >
      <div className="text-2xl flex-shrink-0" aria-hidden="true">
        {arrow}
      </div>
      <div className="flex-1">
        <div className="text-sky-900 font-semibold text-lg">
          {latest.reading.sgv} <span className="text-sm font-normal text-sky-700">{latest.units}</span>
        </div>
        <div className="text-sky-700 text-xs">
          CGM · {time}
        </div>
      </div>
    </div>
  );
}
