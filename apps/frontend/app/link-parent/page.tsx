"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import Header from "@/components/Header";
import type { User } from "@/types";

export default function LinkParentPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    api.me().then(setUser).catch(() => router.push("/login"));
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.linkParent(code);
      setDone(true);
    } catch (e: any) {
      setError(e?.body?.detail || "Не удалось привязаться. Проверь код.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="prism-shell link-parent-console min-h-dvh">
      <Header user={user} backHref="/subjects" title="Привязать родителя" />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer grid overflow-hidden lg:grid-cols-[0.9fr_1.1fr]">
          <aside className="relative min-h-[260px] overflow-hidden border-b border-[color:var(--prism-line)] p-6 lg:border-b-0 lg:border-r lg:p-9">
            <div className="prism-kicker">Parent Link</div>
            <h1 className="mt-4 text-4xl font-black tracking-[-0.06em] text-[color:var(--prism-ink)] sm:text-6xl">Привязать родителя</h1>
            <p className="mt-4 max-w-md text-sm leading-6 text-[color:var(--prism-muted)]">Родитель создаёт код в своём кабинете. Ты вводишь его здесь — после этого он увидит прогресс и рекомендации без доступа к личному чату.</p>
            <div className="prism-orb pointer-events-none absolute -bottom-24 right-4 h-56 w-56 min-h-0 opacity-60" aria-hidden="true" />
          </aside>

          <section className="p-6 sm:p-9">
            {done ? (
              <div className="rounded-[28px] border border-emerald-300/30 bg-emerald-400/10 p-5 text-[color:var(--prism-ink)]">
                <div className="text-3xl font-black">Родитель привязан</div>
                <p className="mt-2 text-sm text-[color:var(--prism-muted)]">Теперь он видит твой прогресс и отчёты.</p>
                <Link href="/subjects" className="prism-action primary mt-5">Вернуться к предметам</Link>
              </div>
            ) : (
              <form onSubmit={submit} className="grid gap-4">
                <label className="grid gap-2">
                  <span className="text-sm font-black text-[color:var(--prism-muted)]">Код от родителя</span>
                  <input
                    type="text"
                    value={code}
                    onChange={(e) => setCode(e.target.value.toUpperCase())}
                    placeholder="P-000123-ABC"
                    required
                    className="prism-input font-mono uppercase tracking-[0.12em]"
                  />
                  <span className="text-xs text-[color:var(--prism-muted)]">Формат обычно похож на P-000123-ABC.</span>
                </label>
                {error && <div className="rounded-2xl border border-rose-300/30 bg-rose-400/10 px-4 py-3 text-sm font-bold text-rose-200">{error}</div>}
                <button type="submit" disabled={busy || !code.trim()} className="prism-action primary w-fit px-6">
                  {busy ? "Привязываю…" : "Привязать"}
                </button>
              </form>
            )}
          </section>
          </div>
        </div>
      </section>
    </main>
  );
}
