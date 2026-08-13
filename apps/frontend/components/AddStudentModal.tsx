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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
      data-testid="add-student-modal"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-student-title"
        tabIndex={-1}
        className="w-full max-w-md rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/95 p-6 shadow-glow focus:outline-none"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="add-student-title" className="text-xl font-black text-[color:var(--prism-ink)]">Создать ученика</h2>
        <p className="mt-1 text-sm text-[color:var(--prism-muted)]">
          Новый ученик автоматически привязывается к общему curriculum 7 класса (или другому, см.
          ниже).
        </p>

        <form onSubmit={submit} className="mt-4 space-y-3">
          <label className="block">
            <span className="block text-sm font-black text-[color:var(--prism-muted)]">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="kid@example.com"
              className="prism-input mt-1 block w-full"
            />
          </label>

          <label className="block">
            <span className="block text-sm font-black text-[color:var(--prism-muted)]">
              Имя (опционально)
            </span>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Кирилл"
              className="prism-input mt-1 block w-full"
            />
          </label>

          <label className="block">
            <span className="block text-sm font-black text-[color:var(--prism-muted)]">Класс</span>
            <select
              value={grade}
              onChange={(e) => setGrade(Number(e.target.value))}
              className="prism-input mt-1 block w-full"
            >
              {[5, 6, 7, 8, 9, 10, 11].map((g) => (
                <option key={g} value={g}>
                  {g} класс
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="block text-sm font-black text-[color:var(--prism-muted)]">
              Временный пароль (передайте ученику)
            </span>
            <div className="mt-1 flex gap-2">
              <input
                type="text"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="prism-input block w-full font-mono"
              />
              <button
                type="button"
                onClick={() => setPassword(autoGeneratePassword())}
                className="prism-action min-h-0 px-3 py-2 text-xs"
              >
                Новый
              </button>
            </div>
          </label>

          {error && (
            <div className="rounded-2xl border border-rose-300/30 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">{error}</div>
          )}

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="prism-action flex-1 px-4 py-2"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={busy || !email || !password}
              className="prism-action primary flex-1 px-4 py-2 disabled:opacity-50"
            >
              {busy ? "Создаю…" : "Создать"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}