"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

async function landingForRole(role: string): Promise<string> {
  switch (role) {
    case "parent": return "/parents";
    case "teacher": return "/teacher";
    case "admin": return "/admin";
    case "student":
    default: return "/subjects";
  }
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && window.localStorage.getItem("ai-tutor-token")) {
      const stored = window.localStorage.getItem("ai-tutor-me");
      const role = stored ? (safeParse(stored)?.role ?? "student") : "student";
      landingForRole(role).then((p) => router.push(p));
    }
  }, [router]);

  function safeParse(raw: string): { role?: string } | null { try { return JSON.parse(raw); } catch { return null; } }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.login({ email, password });
      let role = "student";
      try {
        const me = await api.me();
        role = me.role;
        window.localStorage.setItem("ai-tutor-me", JSON.stringify(me));
      } catch {}
      router.push(await landingForRole(role));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setError("Неверный email или пароль");
      else if (err instanceof ApiError && err.status === 429) {
        const detail = typeof err.body === "object" && err.body !== null && "detail" in err.body
          ? String((err.body as { detail?: unknown }).detail)
          : "Слишком много попыток входа. Подождите и попробуйте снова.";
        setError(detail);
      }
      else setError("Не удалось войти. Проверьте соединение с сервером.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="prism-shell flex min-h-dvh items-center justify-center p-3 sm:p-6">
      <section className="prism-frame grid min-h-[calc(100dvh-32px)] lg:grid-cols-[1.08fr_0.92fr]">
        <div className="prism-layer flex flex-col justify-between p-6 sm:p-10 lg:p-14">
          <div className="prism-topbar -mx-2 -mt-2 border-0 p-0">
            <div className="prism-brand"><span className="prism-mark" /> Prism Tutor</div>
            <span className="prism-pill active">Secure portal</span>
          </div>
          <div className="py-10">
            <div className="prism-kicker">Here and now</div>
            <h1 className="prism-title">Вход в <span className="accent">учебную систему</span></h1>
            <p className="prism-copy">Один портал для ученика, родителя, учителя и администратора. Светлая и тёмная тема работают как полноценные материалы интерфейса.</p>
          </div>
          <div className="prism-bento">
            <Mini label="Student" value="Learn" />
            <Mini label="Parent" value="Track" />
            <Mini label="Teacher" value="Operate" />
          </div>
        </div>

        <div className="prism-layer flex items-center justify-center p-5 sm:p-10">
          <form onSubmit={onSubmit} className="prism-card pad w-full max-w-[480px]">
            <div className="prism-kicker">Authentication</div>
            <h2 className="mt-4 text-4xl font-black tracking-[-0.05em]">С возвращением</h2>
            <p className="mt-2 text-sm text-[color:var(--prism-muted)]">Продолжи маршрут: объяснение → практика → прогресс.</p>

            <div className="prism-field mt-7 space-y-4">
              <label className="block text-sm font-black" htmlFor="email">Email</label>
              <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" placeholder="your@email.com" />
              <label className="block text-sm font-black" htmlFor="password">Пароль</label>
              <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" placeholder="••••••••" />
            </div>

            {error && <div role="alert" className="mt-4 rounded-3xl border border-red-400/30 bg-red-500/10 p-4 text-sm font-bold text-red-500">{error}</div>}

            <button type="submit" disabled={loading} className="prism-action primary mt-6 w-full">
              {loading ? "Входим…" : "Войти"}
            </button>

            <div className="mt-7 space-y-2 text-center text-sm text-[color:var(--prism-muted)]">
              <p>Нет аккаунта? <Link className="font-black text-[color:var(--prism-accent)]" href="/register">Зарегистрироваться</Link></p>
              <p>Забыли пароль? <Link className="font-black text-[color:var(--prism-accent)]" href="/forgot-password">Восстановить</Link></p>
            </div>
          </form>
        </div>
      </section>
    </main>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return <div className="prism-card pad col-span-12 sm:col-span-4"><div className="text-[10px] font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">{label}</div><div className="mt-1 text-2xl font-black">{value}</div></div>;
}
