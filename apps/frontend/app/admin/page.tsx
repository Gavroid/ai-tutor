"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, getToken } from "@/lib/api";
import Header from "@/components/Header";
import type { User } from "@/types";

type AuditEntry = {
  id: number;
  user_id: number | null;
  action: string;
  entity: string | null;
  entity_id: string | null;
  details: string | null;
  ip_address: string | null;
  created_at: string;
};

type Stats = {
  total_users: number;
  active_users: number;
  by_role: { student: number; parent: number; teacher: number; admin: number };
};

type UserItem = {
  id: number;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export default function AdminPage() {
  const [tab, setTab] = useState<"audit" | "users" | "stats" | "tools">("audit");
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [actionFilter, setActionFilter] = useState<string>("");
  const [since, setSince] = useState<string>("");
  const [until, setUntil] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Sprint 5.1: user state для Header (logout button).
  const [current, setCurrent] = useState<User | null>(null);

  useEffect(() => {
    if (!getToken()) return;
    // Sprint 5.1: загружаем текущего юзера для Header.
    api.me().then(setCurrent).catch(() => {});
    refresh(tab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  async function refresh(which: typeof tab) {
    setBusy(true);
    setError(null);
    try {
      if (which === "audit") {
        const data = await api.adminAuditLog({
          limit: 200,
          action: actionFilter || undefined,
          since: since || undefined,
          until: until || undefined,
        });
        setEntries(data);
      } else if (which === "users") {
        const data = await api.adminUsers();
        setUsers(data);
      } else {
        const data = await api.adminStats();
        setStats(data);
      }
    } catch (e: any) {
      setError(e?.body?.detail || "Ошибка загрузки (нужны права админа)");
    } finally {
      setBusy(false);
    }
  }

  async function deactivateUser(uid: number) {
    if (!confirm(`Деактивировать пользователя #${uid}?`)) return;
    try {
      await api.adminDeactivateUser(uid);
      await refresh("users");
    } catch (e: any) {
      alert("Ошибка: " + (e?.body?.detail || "неизвестно"));
    }
  }

  function fmtDetails(d: string | object | null): string {
    if (!d) return "";
    if (typeof d === "object") {
      // JSONB из БД приходит как object (asyncpg + FastAPI сериализует).
      // Sprint 3.0 fix: handle both string and object.
      try {
        return JSON.stringify(d, null, 2);
      } catch {
        return String(d);
      }
    }
    try {
      const obj = JSON.parse(d);
      return JSON.stringify(obj, null, 2);
    } catch {
      return d;
    }
  }

  function fmtDate(iso: string): string {
    return new Date(iso).toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  return (
    <main className="mx-auto max-w-6xl p-6">
      {/* Sprint 5.1: общий Header с logout button */}
      <Header
        user={current}
        backHref="/subjects"
        title="Админ-панель"
      />

      <nav className="mt-4 flex gap-2">
        <Tab active={tab === "audit"} onClick={() => setTab("audit")}>
          Audit log
        </Tab>
        <Tab active={tab === "users"} onClick={() => setTab("users")}>
          Пользователи
        </Tab>
        <Tab active={tab === "stats"} onClick={() => setTab("stats")}>
          Статистика
        </Tab>
        <Tab active={tab === "tools"} onClick={() => setTab("tools")}>
          Инструменты
        </Tab>
      </nav>

      {error && (
        <div className="mt-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
      )}

      <section className="mt-4">
        {busy && <div className="text-sm text-slate-500">Загрузка…</div>}

        {tab === "audit" && !busy && (
          <div className="mb-4 grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm md:grid-cols-4">
            <input
              type="text"
              placeholder="Действие (action)"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            />
            <input
              type="datetime-local"
              value={since}
              onChange={(e) => setSince(e.target.value)}
              placeholder="С даты"
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            />
            <input
              type="datetime-local"
              value={until}
              onChange={(e) => setUntil(e.target.value)}
              placeholder="По дату"
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            />
            <button
              onClick={() => refresh("audit")}
              className="rounded-md bg-sky-600 px-3 py-1 text-sm text-white hover:bg-sky-700"
            >
              Применить
            </button>
          </div>
        )}

        {tab === "audit" && !busy && (
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Когда</th>
                  <th className="px-3 py-2">Действие</th>
                  <th className="px-3 py-2">Объект</th>
                  <th className="px-3 py-2">User</th>
                  <th className="px-3 py-2">IP</th>
                  <th className="px-3 py-2">Details</th>
                </tr>
              </thead>
              <tbody>
                {entries.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-4 text-center text-slate-500">
                      Нет событий
                    </td>
                  </tr>
                )}
                {entries.map((e) => (
                  <tr key={e.id} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-mono text-xs">{fmtDate(e.created_at)}</td>
                    <td className="px-3 py-2">
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">
                        {e.action}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-600">
                      {e.entity}#{e.entity_id ?? "-"}
                    </td>
                    <td className="px-3 py-2 text-xs">{e.user_id ?? "-"}</td>
                    <td className="px-3 py-2 font-mono text-xs text-slate-500">
                      {e.ip_address ?? "-"}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-slate-600">
                      <pre className="max-w-md overflow-x-auto whitespace-pre-wrap">
                        {fmtDetails(e.details)}
                      </pre>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === "users" && !busy && (
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Email</th>
                  <th className="px-3 py-2">Имя</th>
                  <th className="px-3 py-2">Роль</th>
                  <th className="px-3 py-2">Активен</th>
                  <th className="px-3 py-2">Создан</th>
                  <th className="px-3 py-2">Действие</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-mono text-xs">{u.id}</td>
                    <td className="px-3 py-2">{u.email}</td>
                    <td className="px-3 py-2">{u.display_name}</td>
                    <td className="px-3 py-2">
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">
                        {u.role}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {u.is_active ? (
                        <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-800">
                          да
                        </span>
                      ) : (
                        <span className="rounded bg-rose-100 px-1.5 py-0.5 text-xs text-rose-800">
                          нет
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-500">
                      {fmtDate(u.created_at)}
                    </td>
                    <td className="px-3 py-2">
                      {u.is_active && (
                        <button
                          onClick={() => deactivateUser(u.id)}
                          className="rounded bg-rose-100 px-2 py-1 text-xs text-rose-800 hover:bg-rose-200"
                        >
                          Деактивировать
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === "stats" && !busy && stats && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            <Stat label="Всего пользователей" value={stats.total_users} />
            <Stat label="Активных" value={stats.active_users} />
            <Stat label="Учеников" value={stats.by_role.student} />
            <Stat label="Родителей" value={stats.by_role.parent} />
            <Stat label="Учителей" value={stats.by_role.teacher} />
            <Stat label="Админов" value={stats.by_role.admin} />
          </div>
        )}

        {tab === "tools" && !busy && <ToolsTab />}
      </section>
    </main>
  );
}

function Tab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg px-4 py-2 text-sm font-medium ${
        active
          ? "bg-sky-600 text-white"
          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
      }`}
    >
      {children}
    </button>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
    </div>
  );
}

function ToolsTab() {
  const [busy, setBusy] = useState(false);

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">🔧 Диагностика</h3>
        <p className="mt-1 text-sm text-slate-600">
          Завершает диагностические сессии старше TTL (по умолчанию 24ч).
        </p>

        <div className="mt-4">
          <button
            onClick={async () => {
              setBusy(true);
              try {
                await api.adminExpireStaleDiagnostics(24);
                alert("Запущено expire");
              } catch (e) {
                alert("Ошибка: " + (e instanceof Error ? e.message : e));
              } finally {
                setBusy(false);
              }
            }}
            disabled={busy}
            className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
          >
            Завершить старые сессии
          </button>
        </div>
      </div>

      {/* Sprint 3.6.3: AI Kill Switch — emergency stop AI для user */}
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-red-900">🚨 AI Kill Switch</h3>
        <p className="mt-1 text-sm text-red-700">
          Экстренно отключает AI для пользователя. Используй если ребёнок попал в AI-loop
          или AI выдаёт нежелательный контент. После отключения AI endpoints возвращают 503.
        </p>

        <div className="mt-4 space-y-2">
          <div className="flex items-center gap-2">
            <input
              id="kill-switch-user-id"
              type="number"
              min="1"
              placeholder="user_id (например, 4 для Кирилла)"
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              style={{ width: 220 }}
            />
            <button
              onClick={async () => {
                const inp = document.getElementById("kill-switch-user-id") as HTMLInputElement;
                const uid = Number(inp.value);
                if (!uid || uid < 1) {
                  alert("Введи валидный user_id");
                  return;
                }
                setBusy(true);
                try {
                  await api.adminAddAiKillSwitch(uid);
                  alert(`AI kill switch ON для user_id=${uid}`);
                  inp.value = "";
                } catch (e) {
                  alert("Ошибка: " + (e instanceof Error ? e.message : e));
                } finally {
                  setBusy(false);
                }
              }}
              disabled={busy}
              className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              Kill AI
            </button>
            <button
              onClick={async () => {
                setBusy(true);
                try {
                  const r = await api.adminGetAiKillSwitch();
                  alert(`Kill switch ON для: ${JSON.stringify(r.user_ids)}`);
                } catch (e) {
                  alert("Ошибка: " + (e instanceof Error ? e.message : e));
                } finally {
                  setBusy(false);
                }
              }}
              disabled={busy}
              className="rounded-md bg-slate-600 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              Показать список
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}