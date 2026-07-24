"use client";

/**
 * Sprint 44: Public invite landing page.
 *
 * `/invite/[code]` — показывает invite info, предлагает register.
 *
 * UX:
 * - T1D-friendly (calm, welcoming).
 * - aria-live для screen readers.
 * - Если invite invalid — 404-like message.
 * - Кнопка "Зарегистрироваться" ведёт на /register?code=...
 */

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

interface InviteInfo {
  valid: boolean;
  role: string;
  note: string | null;
  expires_at: string | null;
  remaining_uses: number;
}

export default function InviteLandingPage() {
  const params = useParams();
  const router = useRouter();
  const code = params.code as string;

  const [info, setInfo] = useState<InviteInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function validate() {
      try {
        const r = await fetch("/api/v1/auth/redeem-invite", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code }),
        });
        if (!r.ok) {
          const data = await r.json().catch(() => ({}));
          throw new Error(data.detail || "Invite невалиден");
        }
        const data: InviteInfo = await r.json();
        setInfo(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }
    if (code) validate();
  }, [code]);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-50 p-6 flex items-center justify-center">
        <p className="text-slate-500">Проверка кода…</p>
      </main>
    );
  }

  if (error || !info) {
    return (
      <main className="min-h-screen bg-slate-50 p-6 flex items-center justify-center">
        <div className="max-w-md w-full bg-white rounded-2xl border border-rose-200 p-6 text-center">
          <h1 className="text-xl font-semibold text-rose-700 mb-2">
            Приглашение не найдено
          </h1>
          <p className="text-sm text-slate-600 mb-4">
            {error || "Этот код невалиден или уже использован."}
          </p>
          <a
            href="/login"
            className="text-sky-600 hover:underline text-sm"
            data-testid="login-link"
          >
            Войти →
          </a>
        </div>
      </main>
    );
  }

  const roleLabel: Record<string, string> = {
    student: "ученик",
    parent: "родитель",
    teacher: "учитель",
  };

  return (
    <main className="min-h-screen bg-slate-50 p-6 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-2xl border border-sky-200 p-6" data-testid="invite-card">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">
          Добро пожаловать! 👋
        </h1>

        <p className="text-sm text-slate-600 mb-4">
          Тебя пригласили присоединиться к AI-репетитору.
        </p>

        {info.note && (
          <div className="bg-sky-50 border border-sky-200 rounded-lg p-3 mb-4 text-sm text-sky-800">
            <strong>Примечание:</strong> {info.note}
          </div>
        )}

        <dl className="space-y-2 text-sm mb-6">
          <div className="flex justify-between">
            <dt className="text-slate-500">Роль:</dt>
            <dd className="font-medium text-slate-700">
              {roleLabel[info.role] || info.role}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500">Осталось использований:</dt>
            <dd className="font-medium text-slate-700">
              {info.remaining_uses}
            </dd>
          </div>
          {info.expires_at && (
            <div className="flex justify-between">
              <dt className="text-slate-500">Действует до:</dt>
              <dd className="font-medium text-slate-700">
                {new Date(info.expires_at).toLocaleDateString("ru-RU")}
              </dd>
            </div>
          )}
        </dl>

        <button
          type="button"
          onClick={() => router.push(`/register?code=${code}`)}
          className="w-full bg-sky-600 text-white rounded-lg px-4 py-3 font-medium hover:bg-sky-700 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-sky-500"
          data-testid="register-button"
        >
          Зарегистрироваться
        </button>

        <a
          href="/login"
          className="block text-center mt-3 text-sky-600 hover:underline text-sm"
          data-testid="login-link"
        >
          Уже есть аккаунт? Войти
        </a>
      </div>
    </main>
  );
}
