"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useFocusTrap } from "@/lib/use-focus-trap";

interface AddStudentModalProps {
  /** Sprint 7.1: вызывается после успешного создания. */
  onCreated: (newStudent: { id: number; email: string }) => void;
  /** Закрыть модалку. */
  onClose: () => void;
}

/**
 * Sprint 7.1 — модалка для создания нового ученика (admin/teacher).
 *
 * Использует POST /api/v1/auth/register с role=student.
 * Если email занят — показывает ошибку.
 *
 * UI простой: email + display_name + password (или auto-generated).
 */
export default function AddStudentModal({ onCreated, onClose }: AddStudentModalProps) {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [grade, setGrade] = useState(7);
  const [password, setPassword] = useState(autoGeneratePassword());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Sprint 14: focus-trap (Tab зацикливает внутри, Escape закрывает).
  const dialogRef = useFocusTrap({
    active: true,
    onEscape: onClose,
  });

  function autoGeneratePassword(): string {
    // Простой безопасный пароль: 12 chars с uppercase, lowercase, цифрами.
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789";
    let pwd = "";
    for (let i = 0; i < 12; i++) {
      pwd += chars[Math.floor(Math.random() * chars.length)];
    }
    return pwd;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      // POST /api/v1/auth/register
      const user = await api.register({
        email,
        password,
        display_name: displayName || email.split("@")[0],
        role: "student",
      });
      // Sprint 7.1: дополнительно создаём StudentProfile с grade.
      // MVP: profile создаётся автоматически в backend, но grade нужно обновить отдельно.
      // TODO Sprint 7.1+: API для обновления grade (PATCH /api/v1/admin/users/{id}).
      onCreated({ id: (user as { id: number }).id, email });
      onClose();
    } catch (e: unknown) {
      const err = e as { body?: { detail?: string }; message?: string };
      setError(err?.body?.detail || err?.message || "Не удалось создать ученика");
    } finally {
      setBusy(false);
    }
  }

  return (
    // Sprint 14: keyboard-trap (Escape close, Tab циклит), role=dialog, aria-modal=true.
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      data-testid="add-student-modal"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-student-title"
        tabIndex={-1}
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl focus:outline-none"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="add-student-title" className="text-xl font-bold text-slate-900">Создать ученика</h2>
        <p className="mt-1 text-sm text-slate-600">
          Новый ученик автоматически привязывается к общему curriculum 7 класса (или другому, см.
          ниже).
        </p>

        <form onSubmit={submit} className="mt-4 space-y-3">
          <label className="block">
            <span className="block text-sm font-medium text-slate-700">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="kid@example.com"
              className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="block">
            <span className="block text-sm font-medium text-slate-700">
              Имя (опционально)
            </span>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Кирилл"
              className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="block">
            <span className="block text-sm font-medium text-slate-700">Класс</span>
            <select
              value={grade}
              onChange={(e) => setGrade(Number(e.target.value))}
              className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2"
            >
              {[5, 6, 7, 8, 9, 10, 11].map((g) => (
                <option key={g} value={g}>
                  {g} класс
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="block text-sm font-medium text-slate-700">
              Временный пароль (передайте ученику)
            </span>
            <div className="mt-1 flex gap-2">
              <input
                type="text"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="block w-full rounded-md border border-slate-300 px-3 py-2 font-mono"
              />
              <button
                type="button"
                onClick={() => setPassword(autoGeneratePassword())}
                className="rounded-md bg-slate-200 px-3 py-2 text-xs hover:bg-slate-300"
              >
                Новый
              </button>
            </div>
          </label>

          {error && (
            <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>
          )}

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-md bg-slate-100 px-4 py-2 text-slate-700 hover:bg-slate-200"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={busy || !email || !password}
              className="flex-1 rounded-md bg-sky-600 px-4 py-2 font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
            >
              {busy ? "Создаю…" : "Создать"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}