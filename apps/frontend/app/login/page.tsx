"use client";

/**
 * Sprint 106: Login page (2026 design).
 *
 * - Aurora gradient background
 * - Glass card with form
 * - Input + Button from new UI library
 */
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";

// Sprint 11.1: per-role landing page.
async function landingForRole(role: string): Promise<string> {
  switch (role) {
    case "parent":
      return "/parents";
    case "teacher":
      return "/teacher";
    case "admin":
      return "/admin";
    case "student":
    default:
      return "/subjects";
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
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
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
      } catch {
        // fallback
      }
      router.push(await landingForRole(role));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setError("Неверный email или пароль");
      else setError("Не удалось войти. Проверьте соединение с сервером.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-bg p-6">
      {/* Background aurora */}
      <div aria-hidden="true" className="absolute inset-0 -z-10 bg-aurora" />
      <div aria-hidden="true" className="absolute inset-0 -z-10 bg-grid opacity-30" />

      <Card
        variant="glass"
        padding="xl"
        className="w-full max-w-md animate-scale-in"
      >
        <div className="mb-6 text-center">
          <div className="mb-4 inline-flex size-12 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-purple-500 text-2xl">
            🎓
          </div>
          <h1 className="text-display-sm font-bold tracking-tight text-fg">С возвращением</h1>
          <p className="mt-1 text-sm text-fg-muted">AI-репетитор 7 класса</p>
        </div>

        <form className="space-y-4" onSubmit={onSubmit}>
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-fg">
              Email
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="your@email.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-fg">
              Пароль
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-md border border-danger/20 bg-danger/10 px-3 py-2 text-sm text-danger"
            >
              {error}
            </div>
          )}

          <Button type="submit" variant="primary" size="lg" fullWidth loading={loading}>
            {loading ? "Входим…" : "Войти"}
          </Button>
        </form>

        <div className="mt-6 space-y-2 text-center text-sm text-fg-muted">
          <p>
            Нет аккаунта?{" "}
            <Link className="font-medium text-brand-500 hover:underline" href="/register">
              Зарегистрироваться
            </Link>
          </p>
          <p>
            Забыли пароль?{" "}
            <Link className="text-fg-muted underline hover:text-fg" href="/forgot-password">
              Восстановить
            </Link>
          </p>
        </div>
      </Card>
    </main>
  );
}
