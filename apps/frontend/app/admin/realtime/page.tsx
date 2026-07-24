"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken } from "@/lib/api";
import { AdminWSConnection, type AdminSnapshot, type AdminWSState } from "@/lib/admin-ws";

/**
 * Sprint 9.3 — Real-time /admin dashboard.
 *
 * Открывает WebSocket к /api/v1/admin/ws и рендерит:
 * - AI токены (in/out)
 * - AI вызовы по режимам (ok/error)
 * - HTTP 2xx/4xx/5xx
 * - System status (db/redis/backend)
 * - Memory used %
 */
export default function AdminRealtimePage() {
  const router = useRouter();
  const [state, setState] = useState<AdminWSState>({ status: "connecting" });
  const [snap, setSnap] = useState<AdminSnapshot | null>(null);

  useEffect(() => {
    // Sprint 27: cookie auth.
    const conn = new AdminWSConnection(getToken, setState);
    conn.start();
    return () => conn.close();
  }, [router]);

  // Обновляем последний снэпшот когда приходит open state
  useEffect(() => {
    if (state.status === "open") {
      setSnap(state.last);
    }
  }, [state]);

  return (
    <main className="mx-auto max-w-4xl p-6">
      <header className="border-b border-slate-200 pb-4">
        <Link href="/admin" className="text-sm text-sky-600 hover:underline">
          ← Админ-панель
        </Link>
        <h1 className="mt-1 text-2xl font-bold">Real-time метрики</h1>
        <ConnectionStatus state={state} />
      </header>

      {snap === null ? (
        <p className="mt-6 text-sm text-slate-500">
          Ожидание первых данных с Prometheus…
        </p>
      ) : (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
          <KpiCard
            label="AI токены"
            value={
              (snap.ai_tokens.input || 0) + (snap.ai_tokens.output || 0)
            }
            sublabel={`in ${snap.ai_tokens.input || 0} / out ${snap.ai_tokens.output || 0}`}
          />
          <KpiCard
            label="AI вызовы"
            value={Object.values(snap.ai_modes).reduce(
              (sum, m) => sum + (m?.ok || 0) + (m?.error || 0),
              0,
            )}
            sublabel={`${Object.keys(snap.ai_modes).length} режимов`}
          />
          <KpiCard
            label="5xx rate"
            value={snap.http_total["5xx"]}
            sublabel="за всё время"
            danger={snap.http_total["5xx"] > 0}
          />
          <KpiCard
            label="4xx"
            value={snap.http_total["4xx"]}
            sublabel="за всё время"
          />
          <KpiCard
            label="2xx OK"
            value={snap.http_total["2xx"]}
            sublabel="за всё время"
            good
          />
          <KpiCard
            label="Memory used"
            value={
              snap.system.mem_used_pct !== null
                ? `${Math.round(snap.system.mem_used_pct)}%`
                : "—"
            }
            sublabel="System RAM"
          />
        </div>
      )}

      {snap && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">System status</h2>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <ServiceBadge name="DB" status={snap.system.db} />
            <ServiceBadge name="Redis" status={snap.system.redis} />
            <ServiceBadge name="Backend" status={snap.system.backend} />
          </div>
        </section>
      )}

      {snap && Object.keys(snap.ai_modes).length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">AI вызовы по режимам</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 text-left text-xs uppercase text-slate-700">
                <tr>
                  <th className="px-3 py-2">Mode</th>
                  <th className="px-3 py-2">OK</th>
                  <th className="px-3 py-2">Error</th>
                  <th className="px-3 py-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(snap.ai_modes).map(([mode, counts]) => (
                  <tr key={mode} className="border-b">
                    <td className="px-3 py-2 font-medium">{mode}</td>
                    <td className="px-3 py-2 text-emerald-700">{counts?.ok || 0}</td>
                    <td className="px-3 py-2 text-rose-700">{counts?.error || 0}</td>
                    <td className="px-3 py-2">
                      {(counts?.ok || 0) + (counts?.error || 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {snap && (
        <p className="mt-6 text-xs text-slate-500">
          Последний snapshot: {new Date(snap.ts).toLocaleString("ru")}
        </p>
      )}
    </main>
  );
}

function ConnectionStatus({ state }: { state: AdminWSState }) {
  const style = {
    connecting: "bg-amber-100 text-amber-900",
    open: "bg-emerald-100 text-emerald-900",
    closed: "bg-slate-100 text-slate-700",
    error: "bg-rose-100 text-rose-900",
  }[state.status];
  const text = {
    connecting: "Подключение…",
    open: "● Подключено (real-time)",
    closed: `Отключено${state.status === "closed" && state.reason ? `: ${state.reason}` : ""}`,
    error: `Ошибка: ${state.status === "error" ? state.error : ""}`,
  }[state.status];
  return (
    <span className={`mt-2 inline-block rounded px-2 py-1 text-xs font-medium ${style}`}>
      {text}
    </span>
  );
}

function KpiCard({
  label,
  value,
  sublabel,
  danger,
  good,
}: {
  label: string;
  value: string | number;
  sublabel?: string;
  danger?: boolean;
  good?: boolean;
}) {
  const color = danger
    ? "border-rose-300 bg-rose-50"
    : good
      ? "border-emerald-300 bg-emerald-50"
      : "border-slate-200 bg-white";
  return (
    <div className={`rounded-xl border p-4 ${color}`}>
      <div className="text-xs uppercase tracking-wide text-slate-600">{label}</div>
      <div className="mt-1 text-2xl font-bold text-slate-900">{value}</div>
      {sublabel && <div className="mt-1 text-xs text-slate-500">{sublabel}</div>}
    </div>
  );
}

function ServiceBadge({ name, status }: { name: string; status: string }) {
  const isUp = status === "ok";
  return (
    <div
      className={`rounded-lg border p-3 text-center ${
        isUp
          ? "border-emerald-300 bg-emerald-50 text-emerald-900"
          : "border-rose-300 bg-rose-50 text-rose-900"
      }`}
    >
      <div className="text-xs font-medium uppercase">{name}</div>
      <div className="mt-1 text-sm font-bold">{isUp ? "● up" : "● down"}</div>
    </div>
  );
}
