"use client";

/**
 * Sprint 106: Register page (2026 design).
 */
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";

export default function RegisterPage() {
  return (
    <Suspense fallback={<RegisterPageSkeleton />}>
      <RegisterPageInner />
    </Suspense>
  );
}

function RegisterPageSkeleton() {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-bg p-6">
      <div aria-hidden="true" className="absolute inset-0 -z-10 bg-aurora" />
      <Card variant="glass" padding="xl" className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mb-4 inline-flex size-12 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-purple-500 text-2xl">
            🎓
          </div>
          <h1 className="text-display-sm font-bold tracking-tight text-fg">Регистрация</h1>
          <p className="mt-1 text-sm text-fg-muted">Загрузка...</p>
        </div>
      </Card>
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
              : "Проверьте правильность данных";
          setError(msg);
        } else setError("Не удалось зарегистрироваться");
      } else {
        setError("Не удалось зарегистрироваться. Проверьте соединение.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-bg p-6">
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
          <h1 className="text-display-sm font-bold tracking-tight text-fg">
            Создай аккаунт
          </h1>
          <p className="mt-1 text-sm text-fg-muted">И начни заниматься за 2 минуты</p>
        </div>

        {inviteCode && (
          <div
            className="mb-4 rounded-md border border-brand-200 bg-brand-50 p-3 text-sm text-brand-700 dark:border-brand-800 dark:bg-brand-900/20 dark:text-brand-300"
            data-testid="invite-banner"
          >
            🎁 <strong>Приглашение:</strong> ты регистрируешься по коду.
          </div>
        )}

        <form className="space-y-4" onSubmit={onSubmit}>
          <div>
            <label htmlFor="display-name" className="mb-1.5 block text-sm font-medium text-fg">
              Имя или псевдоним
            </label>
            <Input
              id="display-name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
              placeholder="Кирилл"
            />
          </div>

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
              Пароль (от 8 символов)
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label htmlFor="grade" className="mb-1.5 block text-sm font-medium text-fg">
              Класс
            </label>
            <select
              id="grade"
              value={grade}
              onChange={(e) => setGrade(Number(e.target.value))}
              className="flex w-full rounded-md border border-border bg-surface px-3 h-10 text-base text-fg transition-modern focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
            >
              {[5, 6, 7, 8, 9].map((g) => (
                <option key={g} value={g}>{g} класс</option>
              ))}
            </select>
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
            {loading ? "Создаём аккаунт…" : "Зарегистрироваться"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-fg-muted">
          Уже есть аккаунт?{" "}
          <Link className="font-medium text-brand-500 hover:underline" href="/login">
            Войти
          </Link>
        </p>
      </Card>
    </main>
  );
}
