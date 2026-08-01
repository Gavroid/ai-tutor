"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

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

  function safeParse(raw: string): { role?: string } | null {
    try { return JSON.parse(raw); } catch { return null; }
  }

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
      else setError("Не удалось войти. Проверьте соединение с сервером.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="premium-shell flex min-h-screen items-center justify-center p-4 sm:p-8">
      <section className="premium-container grid min-h-[82vh] overflow-hidden rounded-[44px] border border-white/12 bg-white/8 shadow-glow backdrop-blur-2xl lg:grid-cols-[1.08fr_0.92fr]">
        <div className="relative flex flex-col justify-between overflow-hidden p-7 text-white sm:p-10 lg:p-14">
          <div className="absolute inset-0 -z-10 bg-vice-city opacity-90" />
          <div className="premium-kicker w-fit">AI Tutor · Pilot Console</div>
          <div>
            <h1 className="premium-title max-w-3xl text-6xl font-black sm:text-7xl lg:text-8xl">
              Вход в учебный неон.
            </h1>
            <p className="premium-copy mt-6 max-w-xl text-xl">
              Одна точка входа для ученика, родителя, учителя и администратора. Стильно, но без потери учебной ясности.
            </p>
          </div>
          <div className="grid gap-3 text-sm sm:grid-cols-3">
            <LoginMetric label="Контур" value="MVP" />
            <LoginMetric label="Роли" value="4" />
            <LoginMetric label="Фокус" value="Учёба" />
          </div>
        </div>

        <div className="lesson-readable flex items-center justify-center p-6 sm:p-10">
          <div className="w-full max-w-md">
            <div className="mb-7">
              <div className="inline-flex size-14 items-center justify-center rounded-2xl brand-gradient text-3xl text-white shadow-glow">🎓</div>
              <h2 className="mt-5 text-4xl font-black tracking-tight text-[#171022]">С возвращением</h2>
              <p className="mt-2 text-sm text-[#5b4a6f]">Продолжи маршрут: объяснение → практика → прогресс.</p>
            </div>

            <form className="space-y-4" onSubmit={onSubmit}>
              <label className="block text-sm font-bold text-[#2b1248]" htmlFor="email">Email</label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" placeholder="your@email.com" />
              <label className="block text-sm font-bold text-[#2b1248]" htmlFor="password">Пароль</label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" placeholder="••••••••" />

              {error && <div role="alert" className="rounded-2xl border border-danger/20 bg-danger/10 px-4 py-3 text-sm font-semibold text-danger">{error}</div>}

              <Button type="submit" variant="primary" size="lg" fullWidth loading={loading}>
                {loading ? "Входим…" : "Войти"}
              </Button>
            </form>

            <div className="mt-7 space-y-2 text-center text-sm text-[#5b4a6f]">
              <p>Нет аккаунта? <Link className="font-bold text-brand-600 hover:underline" href="/register">Зарегистрироваться</Link></p>
              <p>Забыли пароль? <Link className="font-bold text-brand-600 hover:underline" href="/forgot-password">Восстановить</Link></p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function LoginMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/12 bg-white/10 p-4 backdrop-blur">
      <div className="text-[11px] uppercase tracking-[0.2em] text-white/50">{label}</div>
      <div className="mt-1 text-2xl font-black text-white">{value}</div>
    </div>
  );
}
