"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, getToken } from "@/lib/api";

export default function LinkParentPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  if (!getToken()) {
    if (typeof window !== "undefined") router.push("/login");
    return null;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.linkParent(code);
      setDone(true);
    } catch (e: any) {
      setError(e?.body?.detail || "Не удалось привязаться. Проверь код.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center p-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <Link href="/subjects" className="text-sm text-sky-600 hover:underline">
          ← На главную
        </Link>
        <h1 className="mt-2 text-2xl font-bold">Привязать родителя</h1>
        <p className="mt-1 text-sm text-slate-600">
          Попроси родителя создать код в своём кабинете и введи его здесь.
        </p>

        {done ? (
          <div className="mt-6 rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">
            ✅ Родитель привязан! Теперь он видит твой прогресс в отчётах.
          </div>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <label className="block">
              <span className="block text-sm font-medium text-slate-700">Код от родителя</span>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="P-000123-ABC"
                required
                className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 font-mono uppercase outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
              />
            </label>
            {error && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
            <button
              type="submit"
              disabled={busy || !code.trim()}
              className="w-full rounded-lg bg-sky-600 px-4 py-2.5 font-semibold text-white hover:bg-sky-500 disabled:opacity-60"
            >
              {busy ? "Привязываю…" : "Привязать"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}