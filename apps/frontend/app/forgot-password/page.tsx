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
    e.preventDefault(); setBusy(true); setError(null);
    try { await api.passwordResetRequest(email); setMessage("Если email зарегистрирован, код для сброса уже отправлен."); setStep("confirm"); }
    catch (e: any) { setError(e?.body?.detail || "Не удалось отправить запрос"); }
    finally { setBusy(false); }
  }

  async function handleConfirmSubmit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    if (newPassword !== confirmPassword) { setError("Пароли не совпадают"); return; }
    if (newPassword.length < 8) { setError("Пароль должен быть не менее 8 символов"); return; }
    setBusy(true);
    try { await api.passwordResetConfirm(token, newPassword); setMessage("Пароль изменён. Сейчас откроется вход."); setTimeout(() => { window.location.href = "/login"; }, 1500); }
    catch (e: any) { setError(e?.body?.detail || "Не удалось сбросить пароль"); }
    finally { setBusy(false); }
  }

  return (
    <main className="prism-shell min-h-dvh">
      <section className="mx-auto grid min-h-dvh w-[min(980px,calc(100vw-24px))] place-items-center py-6">
        <div className="w-full overflow-hidden rounded-[34px] border border-[color:var(--prism-line)] bg-[color:var(--prism-elevated)] p-6 shadow-glow sm:p-9">
          <Link href="/login" className="prism-pill">← Войти</Link>
          <div className="prism-kicker mt-8">Доступ</div>
          <h1 className="mt-4 text-4xl font-black tracking-[-0.06em] text-[color:var(--prism-ink)] sm:text-6xl">Восстановление пароля</h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-[color:var(--prism-muted)]">Укажи email, получи код и задай новый пароль. Без белых форм и без потери контраста.</p>

          {message && <div className="mt-5 rounded-2xl border border-emerald-300/30 bg-emerald-400/10 px-4 py-3 text-sm font-bold text-emerald-100">{message}</div>}
          {error && <div className="mt-5 rounded-2xl border border-rose-300/30 bg-rose-400/10 px-4 py-3 text-sm font-bold text-rose-200">{error}</div>}

          {step === "email" && (
            <form onSubmit={handleEmailSubmit} className="mt-6 grid gap-4">
              <label className="grid gap-2"><span className="text-sm font-black text-[color:var(--prism-muted)]">Email</span><input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="prism-input" placeholder="kid@example.com" /></label>
              <button type="submit" disabled={busy} className="prism-action primary w-full">{busy ? "Отправляем…" : "Отправить код"}</button>
            </form>
          )}

          {step === "confirm" && (
            <form onSubmit={handleConfirmSubmit} className="mt-6 grid gap-4">
              <label className="grid gap-2"><span className="text-sm font-black text-[color:var(--prism-muted)]">Код из письма</span><input type="text" required value={token} onChange={(e) => setToken(e.target.value)} className="prism-input font-mono" placeholder="abcdef12..." /></label>
              <label className="grid gap-2"><span className="text-sm font-black text-[color:var(--prism-muted)]">Новый пароль</span><input type="password" required value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="prism-input" minLength={8} /></label>
              <label className="grid gap-2"><span className="text-sm font-black text-[color:var(--prism-muted)]">Повтори пароль</span><input type="password" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="prism-input" minLength={8} /></label>
              <button type="submit" disabled={busy} className="prism-action primary w-full">{busy ? "Сохраняем…" : "Сохранить новый пароль"}</button>
            </form>
          )}
        </div>
      </section>
    </main>
  );
}
