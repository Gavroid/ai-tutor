"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useBadgeToastQueue } from "@/lib/badge-events";
import BadgeToast, { type BadgeToastItem } from "@/components/BadgeToast";

/**
 * Sprint 3.13: глобальный listener событий бейджей.
 *
 * Подписывается на `badgeEvents` и при новом бейдже:
 * 1. Подгружает title/icon из /student/badges/summary (если ещё не было).
 * 2. Показывает BadgeToast в правом нижнем углу.
 *
 * Mount ОДИН раз в layout.tsx — работает на любой странице.
 */
export default function GlobalBadgeToaster() {
  const { pending, ack } = useBadgeToastQueue();
  const [items, setItems] = useState<BadgeToastItem[]>([]);

  // Когда пришло событие — обогащаем slug'ы title/icon и показываем.
  useEffect(() => {
    if (!pending) return;
    let cancelled = false;
    (async () => {
      try {
        const summary = await api.studentBadgesCount();
        const titles = summary.slug_titles;
        const icons = summary.slug_icons;
        const newItems: BadgeToastItem[] = pending.slugs.map((slug) => ({
          slug,
          title: titles[slug] ?? slug,
          icon: icons[slug] ?? "🏅",
        }));
        if (!cancelled) setItems(newItems);
      } catch {
        // Если API недоступен — показываем slug'и как есть.
        if (!cancelled) {
          setItems(
            pending.slugs.map((slug) => ({
              slug,
              title: slug,
              icon: "🏅",
            }))
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pending]);

  return (
    <BadgeToast
      badges={items}
      onDismiss={() => {
        setItems([]);
        ack();
      }}
    />
  );
}
