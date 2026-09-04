"use client";

/**
 * Sprint 3.13: глобальная шина событий для показа toast'а о бейджах
 * с любой страницы.
 *
 * Использование (в любом client-component):
 *   import { badgeEvents } from "@/lib/badge-events";
 *   await api.studentBadgesEvaluate();
 *   badgeEvents.emit(awardedSlugs);
 *
 * И слушать (в GlobalBadgeToaster в layout):
 *   useEffect(() => {
 *     return badgeEvents.subscribe((slugs) => { ... });
 *   }, []);
 *
 * Преимущество — нет prop drilling, работает через модульный singleton.
 */

import { useEffect, useState } from "react";

export interface BadgeEvent {
  /** Slug'и вновь выданных бейджей. */
  slugs: string[];
  /** Время события (для дедупликации в UI). */
  at: number;
}

class BadgeEventBus {
  private listeners: Set<(e: BadgeEvent) => void> = new Set();

  emit(slugs: string[]) {
    if (slugs.length === 0) return;
    const ev: BadgeEvent = { slugs, at: Date.now() };
    this.listeners.forEach((fn) => fn(ev));
  }

  subscribe(fn: (e: BadgeEvent) => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }
}

export const badgeEvents = new BadgeEventBus();

/** React-хелпер: подписка на события бейджей. */
export function useBadgeEvents(handler: (e: BadgeEvent) => void): void {
  useEffect(() => {
    return badgeEvents.subscribe(handler);
  }, []);
}

/**
 * Защита от двойного показа: если тот же набор slug'ов пришёл в течение
 * 2 секунд — игнорируем (race между двумя evaluate вызовами).
 */
export function useBadgeEventDedup(handler: (e: BadgeEvent) => void): void {
  useBadgeEvents((e) => {
    const lastShownAt = lastShown.get(e.slugs.join(","));
    if (lastShownAt && Date.now() - lastShownAt < 2000) return;
    lastShown.set(e.slugs.join(","), Date.now());
    _trimLastShown();
    handler(e);
  });
}

// Sprint 3.15: bound для защиты от неограниченного роста Map (YAGNI LRU — просто clear при > 50).
// Максимум 50 записей — на реальной нагрузке (десятки бейджей/сессию) этот лимит недостижим.
const lastShown = new Map<string, number>();
const MAX_LAST_SHOWN = 50;
function _trimLastShown(): void {
  if (lastShown.size > MAX_LAST_SHOWN) {
    lastShown.clear();
  }
}

/** Хук для текущего списка pending бейджей (для глобального toast). */
export function useBadgeToastQueue(): {
  pending: BadgeEvent | null;
  ack: () => void;
} {
  const [pending, setPending] = useState<BadgeEvent | null>(null);
  useBadgeEventDedup((e) => setPending(e));
  return {
    pending,
    ack: () => setPending(null),
  };
}
