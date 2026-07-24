"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

// Sprint 11.1: per-role landing page.
// parent → /parents (linked children dashboard)
// teacher → /teacher (materials + generate tools)
// admin → /admin (audit + users)
// student → /subjects (default).
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
      // Sprint 11.1: если уже залогинен — сразу на нужную страницу (через /me).
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
      // Sprint 27: cookie ставится автоматически через Set-Cookie header.
      // НЕ сохраняем access_token в localStorage (XSS-safe).
      await api.login({ email, password });
      // Sprint 11.1: запросить /me для определения роли и редиректа.
      let role = "student";
      try {
        const me = await api.me();
        role = me.role;
        window.localStorage.setItem("ai-tutor-me", JSON.stringify(me));
      } catch {
        // если /me не успел — fallback на student
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
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center p-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold">Вход</h1>
        <p className="mt-1 text-sm text-slate-600">AI-репетитор 7 класса</p>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <Field label="Email" type="email" value={email} onChange={setEmail} required />
          <Field label="Пароль" type="password" value={password} onChange={setPassword} required />
          {error && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-sky-600 px-4 py-2.5 font-semibold text-white shadow hover:bg-sky-500 disabled:opacity-60"
          >
            {loading ? "Входим…" : "Войти"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-600">
          Нет аккаунта?{" "}
          <Link className="text-sky-600 underline" href="/register">
            Зарегистрироваться
          </Link>
        </p>
        <p className="mt-2 text-center text-sm text-slate-600">
          Забыли пароль?{" "}
          <Link className="text-sky-600 underline" href="/forgot-password">
            Восстановить
          </Link>
        </p>
      </div>
    </main>
  );
}

function Field(props: {
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-slate-700">{props.label}</span>
      <input
        type={props.type}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        required={props.required}
        className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
      />
    </label>
  );
}