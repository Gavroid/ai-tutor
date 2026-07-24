"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Sprint 44: optional invite code из URL.
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
        // Sprint 44: pass invite code if present.
        ...(inviteCode ? { invite_code: inviteCode } : {}),
      });
      // Sprint 27: cookie ставится через /login Set-Cookie header.
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
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center p-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold">Регистрация</h1>
        <p className="mt-1 text-sm text-slate-600">Создай аккаунт и начни заниматься</p>

        {/* Sprint 44: invite code banner */}
        {inviteCode && (
          <div
            className="mt-4 rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-800"
            data-testid="invite-banner"
          >
            <strong>Приглашение:</strong> ты регистрируешься по приглашению.
          </div>
        )}

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <Field label="Имя или псевдоним" value={displayName} onChange={setDisplayName} required />
          <Field label="Email" type="email" value={email} onChange={setEmail} required />
          <Field label="Пароль (от 8 символов)" type="password" value={password} onChange={setPassword} required />
          <label className="block">
            <span className="block text-sm font-medium text-slate-700">Класс</span>
            <select
              value={grade}
              onChange={(e) => setGrade(Number(e.target.value))}
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            >
              {[5, 6, 7, 8, 9].map((g) => (
                <option key={g} value={g}>{g} класс</option>
              ))}
            </select>
          </label>
          {error && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-sky-600 px-4 py-2.5 font-semibold text-white shadow hover:bg-sky-500 disabled:opacity-60"
          >
            {loading ? "Создаём аккаунт…" : "Зарегистрироваться"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-600">
          Уже есть аккаунт?{" "}
          <Link className="text-sky-600 underline" href="/login">
            Войти
          </Link>
        </p>
      </div>
    </main>
  );
}

function Field(props: {
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-slate-700">{props.label}</span>
      <input
        type={props.type ?? "text"}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        required={props.required}
        className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
      />
    </label>
  );
}