"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AdminSnapshot, AdminWSState } from "@/lib/admin-ws";
import Header from "@/components/Header";
import AddStudentModal from "@/components/AddStudentModal";
import EngagementCard from "@/components/EngagementCard";
import type { User } from "@/types";
import { InvitesTab, RealtimeTab, Stat, Tab, ToolsTab, type Invite } from "./components";

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

type AdminTab = "audit" | "users" | "stats" | "tools" | "invites" | "realtime";


type UserItem = {
  id: number;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export default function AdminPage() {
  const [tab, setTab] = useState<AdminTab>("audit");
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [actionFilter, setActionFilter] = useState<string>("");
  // Sprint 10.4: filter по entity
  const [entityFilter, setEntityFilter] = useState<string>("");
  const [since, setSince] = useState<string>("");
  const [until, setUntil] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Sprint 5.1: user state для Header (logout button).
  const [current, setCurrent] = useState<User | null>(null);
  // Sprint 7.1: state для модалки создания ученика.
  const [showAddStudent, setShowAddStudent] = useState(false);
  // Sprint 9: engagement data.
  const [engagement, setEngagement] = useState<{
    period_days: number;
    active_users: number;
    total_attempts: number;
    avg_attempts_per_active_user: number;
    dau_last_14_days: Array<{ date: string; active_users: number }>;
    top_subjects: Array<{ id: number; name: string; students: number }>;
  } | null>(null);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [invitesLoading, setInvitesLoading] = useState(false);
  const [invitesCreating, setInvitesCreating] = useState(false);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [inviteRole, setInviteRole] = useState<"student" | "parent" | "teacher">("student");
  const [inviteNote, setInviteNote] = useState("");
  const [inviteExpiresInDays, setInviteExpiresInDays] = useState("");
  const [inviteMaxUses, setInviteMaxUses] = useState(1);
  const [realtimeState, setRealtimeState] = useState<AdminWSState>({ status: "closed", reason: "not-opened" });
  const [realtimeSnapshot, setRealtimeSnapshot] = useState<AdminSnapshot | null>(null);
  const [realtimeLoading, setRealtimeLoading] = useState(false);

  useEffect(() => {
    const requestedTab = new URLSearchParams(window.location.search).get("tab");
    if (requestedTab === "audit" || requestedTab === "users" || requestedTab === "stats" || requestedTab === "tools" || requestedTab === "invites" || requestedTab === "realtime") {
      setTab(requestedTab);
      window.history.replaceState(null, "", "/admin");
    }
  }, []);

  useEffect(() => {
    // Sprint 27: cookie auth.
    // Sprint 5.1: загружаем текущего юзера для Header.
    api.me().then(setCurrent).catch(() => {});
    refresh(tab);
    // Sprint 9: load engagement (admin only).
    if (current?.role === "admin") {
      fetch("/api/v1/admin/engagement?days=30", {
        credentials: "include",
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => setEngagement(d))
        .catch(() => {});
    }
  }, [tab, current?.role]);

  async function refreshRealtimeSnapshot() {
    if (current?.role !== "admin") {
      setRealtimeState({ status: "error", error: "Admin session required" });
      return;
    }
    setRealtimeLoading(true);
    setRealtimeState((currentState) =>
      realtimeSnapshot && currentState.status === "open" ? currentState : { status: "connecting" },
    );
    try {
      const response = await fetch("/api/v1/admin/realtime/snapshot", {
        credentials: "include",
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const snapshot = (await response.json()) as AdminSnapshot;
      setRealtimeSnapshot(snapshot);
      setRealtimeState({ status: "open", last: snapshot });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Snapshot error";
      setRealtimeState((currentState) =>
        realtimeSnapshot && currentState.status === "open" ? currentState : { status: "error", error: message },
      );
    } finally {
      setRealtimeLoading(false);
    }
  }

  useEffect(() => {
    if (tab !== "realtime" || current?.role !== "admin" || realtimeSnapshot) return;
    void refreshRealtimeSnapshot();
  }, [tab, current?.role]);

  async function refresh(which: AdminTab) {
    setBusy(true);
    setError(null);
    try {
      if (which === "audit") {
        const data = await api.adminAuditLog({
          limit: 200,
          action: actionFilter || undefined,
          // Sprint 10.4: filter по entity
          entity: entityFilter || undefined,
          since: since || undefined,
          until: until || undefined,
        });
        setEntries(data);
      } else if (which === "users") {
        const data = await api.adminUsers();
        setUsers(data);
      } else if (which === "stats") {
        const data = await api.adminStats();
        setStats(data);
      } else if (which === "invites") {
        await loadInvites();
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

  async function loadInvites() {
    setInvitesLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/admin/invites?limit=50", { credentials: "include" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setInvites(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setInvitesLoading(false);
    }
  }

  async function createInvite(e: React.FormEvent) {
    e.preventDefault();
    setInvitesCreating(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { role: inviteRole, max_uses: inviteMaxUses };
      if (inviteNote.trim()) body.note = inviteNote.trim();
      if (inviteExpiresInDays && parseInt(inviteExpiresInDays) > 0) body.expires_in_days = parseInt(inviteExpiresInDays);
      const response = await fetch("/api/v1/admin/invites", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      const invite = await response.json();
      setInvites([invite, ...invites]);
      setInviteNote("");
      setInviteExpiresInDays("");
      setInviteMaxUses(1);
      await navigator.clipboard.writeText(invite.code);
      setCopiedCode(invite.code);
      setTimeout(() => setCopiedCode(null), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setInvitesCreating(false);
    }
  }

  async function deleteInvite(code: string) {
    if (!confirm(`Удалить invite ${code}?`)) return;
    setError(null);
    try {
      const response = await fetch(`/api/v1/admin/invites/${code}`, { method: "DELETE", credentials: "include" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setInvites(invites.filter((invite) => invite.code !== code));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  }

  async function copyInvite(code: string) {
    await navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
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
    <main className="prism-shell admin-console min-h-dvh">
      <Header
        user={current}
        backHref="/subjects"
        title="Админ-панель"
      />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer p-5 lg:p-10">
      {/* S1 (2026-09-01): убран overflow-x-auto — он создавал clipping табов
          сверху при scroll restoration. 6 табов при ширине ≥1024px
          помещаются в один ряд без horizontal scroll. На узких экранах
          flex-wrap автоматически переносит табы. */}
      <div className="-mx-2 px-2 pb-2">
        <nav className="flex flex-wrap min-w-max gap-2 sm:gap-2">
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
        <Tab active={tab === "invites"} onClick={() => setTab("invites")}>
          Invites
        </Tab>
        <Tab active={tab === "realtime"} onClick={() => setTab("realtime")}>
          Realtime
        </Tab>
        <a
          href="/admin/ai-providers"
          className="px-3 py-1.5 rounded-lg text-sm font-medium border border-[var(--border)] hover:bg-[var(--surface)] no-underline"
        >
          AI-провайдеры →
        </a>
        </nav>
      </div>

      {error && (
        <div className="mt-4 rounded-2xl border border-rose-400/30 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</div>
      )}

      <section className="admin-content-zone mt-4">
        {busy && <div className="text-sm text-[color:var(--prism-muted)]">Загрузка…</div>}

        {tab === "audit" && !busy && (
          <div className="admin-panel-surface mb-4 grid grid-cols-1 gap-3 p-3 lg:grid-cols-[1fr_1fr_220px_220px_auto]">
            <input
              type="text"
              placeholder="action (например, login_success)"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            />
            {/* Sprint 10.4: filter по entity */}
            <input
              type="text"
              placeholder="entity (например, user или material)"
              value={entityFilter}
              onChange={(e) => setEntityFilter(e.target.value)}
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
              className="prism-action primary min-h-0 px-4 py-2 text-sm"
            >
              Применить
            </button>
          </div>
        )}

        {tab === "audit" && !busy && (
          <div className="admin-panel-surface prism-scroll w-full overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-[color:var(--prism-muted)]">
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
                    <td colSpan={6} className="px-3 py-4 text-center text-[color:var(--prism-muted)]">
                      Нет событий
                    </td>
                  </tr>
                )}
                {entries.map((e) => (
                  <tr key={e.id} className="border-t border-[color:var(--prism-line)]">
                    <td className="px-3 py-2 font-mono text-xs">{fmtDate(e.created_at)}</td>
                    <td className="px-3 py-2">
                      <span className="rounded-full border border-[color:var(--prism-line)] bg-black/10 px-2 py-0.5 font-mono text-xs text-[color:var(--prism-ink)]">
                        {e.action}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-[color:var(--prism-muted)]">
                      {e.entity}#{e.entity_id ?? "-"}
                    </td>
                    <td className="px-3 py-2 text-xs">{e.user_id ?? "-"}</td>
                    <td className="px-3 py-2 font-mono text-xs text-[color:var(--prism-muted)]">
                      {e.ip_address ?? "-"}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-[color:var(--prism-muted)]">
                      <pre className="min-w-[360px] max-w-4xl overflow-x-auto whitespace-pre-wrap">
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
          <div className="space-y-3">
            {/* Sprint 7.1: кнопка добавления ученика */}
            <div className="flex justify-end">
              <button
                onClick={() => setShowAddStudent(true)}
                data-testid="add-student-button"
                className="prism-action primary text-sm"
              >
                + Создать ученика
              </button>
            </div>
            <div className="admin-panel-surface prism-scroll w-full overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-[color:var(--prism-muted)]">
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
                  <tr key={u.id} className="border-t border-[color:var(--prism-line)]">
                    <td className="px-3 py-2 font-mono text-xs">{u.id}</td>
                    <td className="px-3 py-2">{u.email}</td>
                    <td className="px-3 py-2">{u.display_name}</td>
                    <td className="px-3 py-2">
                      <span className="rounded-full border border-[color:var(--prism-line)] bg-black/10 px-2 py-0.5 font-mono text-xs text-[color:var(--prism-ink)]">
                        {u.role}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {u.is_active ? (
                        <span className="rounded-full border border-[color:var(--prism-line)] bg-black/10 px-2 py-0.5 text-xs text-[color:var(--prism-green)]">
                          да
                        </span>
                      ) : (
                        <span className="rounded-full border border-[color:var(--prism-line)] bg-black/10 px-2 py-0.5 text-xs text-rose-200">
                          нет
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-xs text-[color:var(--prism-muted)]">
                      {fmtDate(u.created_at)}
                    </td>
                    <td className="px-3 py-2">
                      {u.is_active && (
                        <button
                          onClick={() => deactivateUser(u.id)}
                          className="prism-pill hover-danger min-h-0 px-3 py-1 text-xs"
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
          </div>
        )}

        {showAddStudent && (
          <AddStudentModal
            onClose={() => setShowAddStudent(false)}
            onCreated={() => {
              refresh("users");
            }}
          />
        )}

        {tab === "stats" && !busy && stats && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
              <Stat label="Всего пользователей" value={stats.total_users} />
              <Stat label="Активных" value={stats.active_users} />
              <Stat label="Учеников" value={stats.by_role.student} />
              <Stat label="Родителей" value={stats.by_role.parent} />
              <Stat label="Учителей" value={stats.by_role.teacher} />
              <Stat label="Админов" value={stats.by_role.admin} />
            </div>
            {/* Sprint 9: engagement metrics */}
            {engagement && <EngagementCard data={engagement} />}
          </div>
        )}

        {tab === "tools" && !busy && <ToolsTab />}

        {tab === "invites" && !busy && (
          <InvitesTab
            invites={invites}
            loading={invitesLoading}
            creating={invitesCreating}
            copiedCode={copiedCode}
            role={inviteRole}
            note={inviteNote}
            expiresInDays={inviteExpiresInDays}
            maxUses={inviteMaxUses}
            onRoleChange={setInviteRole}
            onNoteChange={setInviteNote}
            onExpiresChange={setInviteExpiresInDays}
            onMaxUsesChange={setInviteMaxUses}
            onCreate={createInvite}
            onCopy={copyInvite}
            onDelete={deleteInvite}
          />
        )}

        {tab === "realtime" && !busy && <RealtimeTab state={realtimeState} snapshot={realtimeSnapshot} loading={realtimeLoading} onRefresh={refreshRealtimeSnapshot} />}
      </section>
    </div></div></section></main>
  );
}

