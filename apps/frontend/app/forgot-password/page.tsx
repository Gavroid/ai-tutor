"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<"email" | "confirm">("email");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.passwordResetRequest(email);
      setMessage(
        "Если этот email зарегистрирован, мы отправили на него код для сброса. Проверьте почту."
      );
      setStep("confirm");
    } catch (e: any) {
      setError(e?.body?.detail || "Не удалось отправить запрос");
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirmSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("Пароли не совпадают");
      return;
    }
    if (newPassword.length < 8) {
      setError("Пароль должен быть не менее 8 символов");
      return;
    }

    setBusy(true);
    try {
      await api.passwordResetConfirm(token, newPassword);
      setMessage("Пароль успешно изменён! Теперь можно войти.");
      setTimeout(() => {
        window.location.href = "/login";
      }, 1500);
    } catch (e: any) {
      setError(e?.body?.detail || "Не удалось сбросить пароль");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto mt-16 max-w-md p-6">
      <h1 className="mb-2 text-2xl font-bold">Восстановление пароля</h1>
      <p className="mb-6 text-sm text-slate-600">
        Забыли пароль? Не проблема. Укажите email — мы пришлём код для сброса.
      </p>

      {message && (
        <div className="mb-4 rounded-md bg-emerald-50 p-3 text-sm text-emerald-700">
          {message}
        </div>
      )}
      {error && (
        <div className="mb-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {step === "email" && (
        <form onSubmit={handleEmailSubmit} className="space-y-3">
          <label className="block text-sm font-medium text-slate-700">
            Email
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border border-slate-300 p-2"
              placeholder="kid@example.com"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-md bg-sky-600 px-4 py-2 text-white hover:bg-sky-700 disabled:opacity-50"
          >
            {busy ? "Отправляем…" : "Отправить код"}
          </button>
          <Link
            href="/login"
            className="block text-center text-sm text-sky-600 hover:underline"
          >
            Вспомнил пароль? Войти
          </Link>
        </form>
      )}

      {step === "confirm" && (
        <form onSubmit={handleConfirmSubmit} className="space-y-3">
          <label className="block text-sm font-medium text-slate-700">
            Код из письма
            <input
              type="text"
              required
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="mt-1 block w-full rounded-md border border-slate-300 p-2 font-mono"
              placeholder="abcdef12..."
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Новый пароль (≥ 8 символов)
            <input
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border border-slate-300 p-2"
              minLength={8}
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Повторите пароль
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border border-slate-300 p-2"
              minLength={8}
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-md bg-sky-600 px-4 py-2 text-white hover:bg-sky-700 disabled:opacity-50"
          >
            {busy ? "Сохраняем…" : "Сохранить новый пароль"}
          </button>
        </form>
      )}
    </main>
  );
}
