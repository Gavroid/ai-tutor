"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

export default function RegisterPage() {
  return (
    <Suspense fallback={<RegisterSkeleton />}>
      <RegisterPageInner />
    </Suspense>
  );
}

function RegisterSkeleton() {
  return (
    <main className="prism-shell grid min-h-dvh place-items-center p-4">
      <section className="prism-card pad w-full max-w-xl">Загрузка…</section>
    </main>
  );
}

function RegisterPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const inviteCode = searchParams.get("code");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [grade, setGrade] = useState(7);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.register({
        email,
        password,
        display_name: displayName,
        role: "student",
        grade,
        ...(inviteCode ? { invite_code: inviteCode } : {}),
      });
      await api.login({ email, password });
      router.push("/subjects");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) setError("Пользователь с таким email уже зарегистрирован");
        else if (err.status === 422) {
          const detail = (err.body as any)?.detail;
          const msg = Array.isArray(detail)
            ? detail.map((d: any) => d.msg || d).join("; ")
            : typeof detail === "string"
              ? detail
              : "Проверь правильность данных";
          setError(msg);
        } else setError("Не удалось зарегистрироваться");
      } else {
        setError("Не удалось зарегистрироваться. Проверь соединение.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="prism-shell min-h-dvh">
      <section className="mx-auto grid min-h-dvh w-[min(1180px,calc(100vw-24px))] place-items-center py-6">
        <div className="grid w-full overflow-hidden rounded-[34px] border border-[color:var(--prism-line)] bg-[color:var(--prism-elevated)] shadow-glow lg:grid-cols-[0.9fr_1.1fr]">
          <aside className="relative min-h-[300px] overflow-hidden border-b border-[color:var(--prism-line)] p-6 lg:border-b-0 lg:border-r lg:p-9">
            <Link href="/login" className="prism-pill">← Войти</Link>
            <div className="prism-kicker mt-9">Новый ученик</div>
            <h1 className="mt-4 text-4xl font-black tracking-[-0.06em] text-[color:var(--prism-ink)] sm:text-6xl">Создай аккаунт</h1>
            <p className="mt-4 max-w-md text-sm leading-6 text-[color:var(--prism-muted)]">Имя, почта, пароль и класс — после регистрации сразу откроется карта обучения.</p>
            {inviteCode && <div className="mt-5 rounded-2xl border border-[color:var(--prism-line)] bg-black/10 px-4 py-3 text-sm text-[color:var(--prism-muted)]">Регистрация по приглашению: <b className="text-[color:var(--prism-ink)]">{inviteCode}</b></div>}
            <div className="prism-orb pointer-events-none absolute -bottom-28 right-0 h-60 w-60 min-h-0 opacity-55" aria-hidden="true" />
          </aside>

          <section className="p-6 sm:p-9">
            <form className="grid gap-4" onSubmit={onSubmit}>
              <label className="grid gap-2">
                <span className="text-sm font-black text-[color:var(--prism-muted)]">Имя или псевдоним</span>
                <input className="prism-input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required placeholder="Кирилл" />
              </label>
              <label className="grid gap-2">
                <span className="text-sm font-black text-[color:var(--prism-muted)]">Email</span>
                <input className="prism-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" placeholder="your@email.com" />
              </label>
              <label className="grid gap-2">
                <span className="text-sm font-black text-[color:var(--prism-muted)]">Пароль</span>
                <input className="prism-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" placeholder="Минимум 8 символов" />
              </label>
              <label className="grid gap-2">
                <span className="text-sm font-black text-[color:var(--prism-muted)]">Класс</span>
                <select className="prism-input" value={grade} onChange={(e) => setGrade(Number(e.target.value))}>
                  {[5, 6, 7, 8, 9].map((g) => <option key={g} value={g}>{g} класс</option>)}
                </select>
              </label>
              {error && <div role="alert" className="rounded-2xl border border-rose-300/30 bg-rose-400/10 px-4 py-3 text-sm font-bold text-rose-200">{error}</div>}
              <button type="submit" className="prism-action primary w-full" disabled={loading}>
                {loading ? "Создаём аккаунт…" : "Зарегистрироваться"}
              </button>
            </form>
            <p className="mt-5 text-center text-sm text-[color:var(--prism-muted)]">Уже есть аккаунт? <Link className="font-black text-[color:var(--prism-cyan)] hover:underline" href="/login">Войти</Link></p>
          </section>
        </div>
      </section>
    </main>
  );
}
