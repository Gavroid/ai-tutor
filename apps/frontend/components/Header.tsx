"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { User } from "@/types";

interface HeaderProps {
  user: User | null;
  backHref?: string;
  title?: string;
  backLabel?: string;
  // Sprint 3.11: badge count для ученика (если не передан — Header сам
  // дёрнет /api/v1/student/badges/summary на mount). parent/admin — не нужно.
  badgeCount?: number;
  badgeTotal?: number;
}

export default function Header({
  user,
  backHref,
  title,
  backLabel = "Назад",
  badgeCount: badgeCountProp,
  badgeTotal: badgeTotalProp,
}: HeaderProps) {
  const router = useRouter();
  const [badgeCount, setBadgeCount] = useState<number | undefined>(
    badgeCountProp
  );
  const [badgeTotal, setBadgeTotal] = useState<number | undefined>(
    badgeTotalProp
  );

  // Sprint 3.11: догружаем badge count если не передан через prop.
  // Делаем ТОЛЬКО для ученика (другие роли не получают /api/v1/student/...).
  useEffect(() => {
    if (badgeCountProp !== undefined) return; // уже задан
    if (user?.role !== "student") return;
    let cancelled = false;
    api.studentBadgesCount()
      .then((s) => {
        if (!cancelled) {
          setBadgeCount(s.earned);
          setBadgeTotal(s.available);
        }
      })
      .catch((err) => {
        // 401 для anonymous — это нормально (на login-странице Header ещё есть).
        if (err instanceof ApiError && err.status === 401) return;
        // Тихо игнорируем, чтобы не шуметь в консоли.
      });
    return () => {
      cancelled = true;
    };
  }, [user?.role, badgeCountProp]);

  // Sprint 3.13: подписываемся на глобальные события бейджей — при новом
  // бейдже обновляем pill счётчик без отдельного запроса.
  useEffect(() => {
    if (user?.role !== "student") return;
    let cancelled = false;
    let cleanup: (() => void) | undefined;
    (async () => {
      const { badgeEvents } = await import("@/lib/badge-events");
      const off = badgeEvents.subscribe(() => {
        if (cancelled) return;
        api.studentBadgesCount()
          .then((s) => {
            if (!cancelled) {
              setBadgeCount(s.earned);
              setBadgeTotal(s.available);
            }
          })
          .catch(() => {});
      });
      cleanup = off;
    })();
    return () => {
      cancelled = true;
      cleanup?.();
    };
  }, [user?.role]);

  async function logout() {
    try { await api.logout(); } catch {}
    router.push("/login");
  }

  const isStudent = user?.role === "student";
  const showBadgePill =
    isStudent && typeof badgeCount === "number" && badgeCount >= 0;

  return (
    <header className="sticky top-0 z-40 border-b border-[color:var(--prism-line)] bg-[color-mix(in_srgb,var(--prism-panel-solid)_76%,transparent)] backdrop-blur-2xl">
      <div className="mx-auto flex min-h-[68px] w-full max-w-[1840px] items-center justify-between gap-3 px-3 py-3 sm:px-4">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <Link href="/subjects" className="prism-brand shrink-0">
            <span className="prism-mark" />
            <span className="hidden sm:inline">Prism Tutor</span>
          </Link>
          {backHref && (
            <Link href={backHref} className="prism-pill hidden sm:inline-flex">← {backLabel}</Link>
          )}
          {title && <h1 className="truncate text-sm font-black tracking-[-0.02em] text-[color:var(--prism-ink)] sm:text-base">{title}</h1>}
        </div>

        <div className="flex shrink-0 items-center justify-end gap-2">
          {/* Sprint 3.11: пилюля с прогрессом по бейджам (только для student). */}
          {showBadgePill && (
            <Link
              href="/student/badges"
              className="prism-pill hidden sm:inline-flex items-center gap-2"
              aria-label={`Бейджи: ${badgeCount} из ${badgeTotal ?? "?"}`}
              data-testid="header-badges-pill"
            >
              <span aria-hidden>🏅</span>
              <span className="font-black tabular-nums">
                {badgeCount}
                {typeof badgeTotal === "number" && badgeTotal > 0 && (
                  <span className="text-[color:var(--prism-muted)]"> / {badgeTotal}</span>
                )}
              </span>
            </Link>
          )}
          {user && <a href="/feedback" className="prism-pill hidden sm:inline-flex" aria-label="Оставить фидбек об уроке">💬 Фидбек</a>}
          {/* Sprint 3.9.2: ThemeToggle убран — только тёмная тема. */}
          {user && <span className="prism-pill hidden md:inline-flex">{user.role} · {user.display_name || user.email}</span>}
          {user && <button onClick={logout} className="prism-action">Выйти</button>}
        </div>
      </div>
    </header>
  );
}
