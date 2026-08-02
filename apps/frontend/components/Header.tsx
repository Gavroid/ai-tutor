"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { User } from "@/types";
import ThemeToggle from "@/components/ThemeToggle";

interface HeaderProps {
  user: User | null;
  backHref?: string;
  title?: string;
  backLabel?: string;
}

export default function Header({ user, backHref, title, backLabel = "Назад" }: HeaderProps) {
  const router = useRouter();

  async function logout() {
    try { await api.logout(); } catch {}
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-40 border-b border-[color:var(--prism-line)] bg-[color-mix(in_srgb,var(--prism-panel-solid)_76%,transparent)] backdrop-blur-2xl">
      <div className="mx-auto flex min-h-[68px] w-[min(1840px,calc(100vw-20px))] items-center justify-between gap-3 px-2 py-3 sm:px-4">
        <div className="flex min-w-0 items-center gap-3">
          <Link href="/subjects" className="prism-brand shrink-0">
            <span className="prism-mark" />
            <span className="hidden sm:inline">Prism Tutor</span>
          </Link>
          {backHref && (
            <Link href={backHref} className="prism-pill hidden sm:inline-flex">← {backLabel}</Link>
          )}
          {title && <h1 className="truncate text-sm font-black tracking-[-0.02em] text-[color:var(--prism-ink)] sm:text-base">{title}</h1>}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {user && <span className="prism-pill hidden md:inline-flex">{user.role}</span>}
          <ThemeToggle />
          {user && <button onClick={logout} className="prism-action">Выйти</button>}
        </div>
      </div>
    </header>
  );
}
