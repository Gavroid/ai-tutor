"use client";

/**
 * Sprint 108: Header component (2026 design).
 *
 * - Glass background with subtle border
 * - Avatar + name + role badge
 * - Logout button uses new Button component
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { User } from "@/types";
import { Button } from "@/components/ui/Button";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";

interface HeaderProps {
  user: User | null;
  backHref?: string;
  title?: string;
  backLabel?: string;
}

export default function Header({ user, backHref, title, backLabel = "Назад" }: HeaderProps) {
  const router = useRouter();

  async function logout() {
    try {
      await api.logout();
    } catch {
      // ignore
    }
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-30 border-b border-white/15 bg-[color-mix(in_srgb,var(--color-bg)_82%,transparent)] text-white shadow-glow backdrop-blur-xl">
      <div className="mx-auto flex w-[min(1720px,calc(100vw-24px))] items-center justify-between px-2 py-3 sm:px-4">
        <div className="flex items-center gap-3">
          {backHref && (
            <Link
              href={backHref}
              className="flex items-center gap-1 text-sm text-white/75 transition-modern hover:text-white"
            >
              <span aria-hidden>←</span> {backLabel}
            </Link>
          )}
          {title && (
            <h1 className="neon-text text-lg font-semibold tracking-tight md:text-xl">
              {title}
            </h1>
          )}
        </div>

        {user && (
          <div className="flex items-center gap-3">
            <div className="hidden text-right text-xs sm:block">
              <div className="font-medium text-white">
                {user.display_name || user.email}
              </div>
              <div className="mt-0.5 flex justify-end">
                <Badge variant="brand" size="sm">
                  {user.role}
                </Badge>
              </div>
            </div>
            <Avatar
              name={user.display_name || user.email || "?"}
              size="md"
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={logout}
              className="text-white hover:bg-white/10 hover:text-white"
            >
              Выйти
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
