"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { User } from "@/types";

interface HeaderProps {
  user: User | null;
  /** Ссылка «← Назад» слева (опционально). */
  backHref?: string;
  /** Заголовок страницы. */
  title?: string;
}

/**
 * Sprint 5.1 — общий Header с logout button.
 * Sprint 27 — logout вызывает /auth/logout (backend очищает cookies).
 */
export default function Header({ user, backHref, title }: HeaderProps) {
  const router = useRouter();

  async function logout() {
    // Sprint 27: cookie очищается на backend через /auth/logout.
    try {
      await api.logout();
    } catch {
      // ignore — перенаправляем в /login в любом случае.
    }
    router.push("/login");
  }

  return (
    <header className="border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between">
        <div className="flex items-center gap-3">
          {backHref && (
            <Link
              href={backHref}
              className="text-sm text-sky-600 hover:underline"
            >
              ← Назад
            </Link>
          )}
          {title && (
            <h1 className="text-xl font-bold text-slate-900">{title}</h1>
          )}
        </div>

        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right text-xs">
              <div className="font-medium text-slate-900">
                {user.display_name || user.email}
              </div>
              <div className="text-slate-500">
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] uppercase tracking-wide">
                  {user.role}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={logout}
              data-testid="logout-button"
              className="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-rose-100 hover:text-rose-700"
            >
              Выйти
            </button>
          </div>
        )}
      </div>
    </header>
  );
}