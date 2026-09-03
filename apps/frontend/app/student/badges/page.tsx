"use client";

// Sprint 3.10 — редизайн /student/badges под prism-shell.
// Sprint 7.1: парсим markdown в реальном времени во время WS-стрима.
// Sprint 3.11: user передаётся в Header чтобы показывался pill бейджей.

import { useEffect, useState } from "react";
import Header from "@/components/Header";
import { api } from "@/lib/api";
import type { User } from "@/types";
import StudentBadgesClient from "./client";

export default function StudentBadgesPage() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api
      .me()
      .then((u) => setUser(u))
      .catch(() => setUser(null));
  }, []);

  return (
    <main className="prism-shell admin-console min-h-dvh">
      <Header user={user} backHref="/subjects" backLabel="К предметам" title="Достижения" />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer p-5 lg:p-10">
            {/* Sprint 3.10: оборачиваем в admin-content-zone для scroll
                (как у /admin/ai-providers Sprint 3.9.6.2). */}
            <section className="admin-content-zone mt-4 space-y-6">
              <div className="prism-kicker">Sprint 3.10 · Gamification</div>
              <h1 className="text-3xl font-black tracking-[-0.04em] text-[color:var(--prism-ink)]">
                Достижения и серии
              </h1>
              <p className="text-sm leading-6 text-[color:var(--prism-muted)] max-w-3xl">
                Баджи за <strong>усилие</strong>, а не за streak — за возвращение к сложному, за своими словами,
                за разнообразие предметов. Получай их, пробуя новое.
                {user?.display_name && (
                  <> Текущий пользователь: <strong>{user.display_name}</strong>.</>
                )}
              </p>
              <StudentBadgesClient />
            </section>
          </div>
        </div>
      </section>
    </main>
  );
}
