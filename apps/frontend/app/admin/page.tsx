"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AdminSnapshot, AdminWSState } from "@/lib/admin-ws";
import Header from "@/components/Header";
import AddStudentModal from "@/components/AddStudentModal";
import EngagementCard from "@/components/EngagementCard";
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

type AdminTab = "audit" | "users" | "stats" | "tools" | "invites" | "realtime";

type Invite = {
  code: string;
  role: string;
  note: string | null;
  expires_at: string | null;
  max_uses: number;
  uses_count: number;
  created_at: string;
  is_valid: boolean;
  is_expired: boolean;
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
  const realtimeFailuresRef = useRef(0);
  const realtimeHasSnapshotRef = useRef(false);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, current?.role]);

  useEffect(() => {
    if (tab !== "realtime") return;
    if (current?.role !== "admin") {
      setRealtimeState({ status: "connecting" });
      return;
    }
    let cancelled = false;
    let timer: number | null = null;

    async function loadSnapshot() {
      try {
        setRealtimeState((currentState) =>
          currentState.status === "open" ? currentState : { status: "connecting" },
        );
        const response = await fetch("/api/v1/admin/realtime/snapshot", {
          credentials: "include",
          cache: "no-store",
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const snapshot = (await response.json()) as AdminSnapshot;
        if (cancelled) return;
        realtimeFailuresRef.current = 0;
        realtimeHasSnapshotRef.current = true;
        setRealtimeSnapshot(snapshot);
        setRealtimeState({ status: "open", last: snapshot });
      } catch (error) {
        if (cancelled) return;
        realtimeFailuresRef.current += 1;
        const message = error instanceof Error ? error.message : "Polling error";
        setRealtimeState((currentState) => {
          if (currentState.status === "open" || realtimeHasSnapshotRef.current) return currentState;
          return realtimeFailuresRef.current >= 3
            ? { status: "error", error: message }
            : { status: "connecting" };
        });
      }
    }

    void loadSnapshot();
    timer = window.setInterval(loadSnapshot, 3000);
    return () => {
      cancelled = true;
      if (timer) window.clearInterval(timer);
    };
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
      <nav className="flex gap-2">
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
      </nav>

      {error && (
        <div className="mt-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
      )}

      <section className="admin-content-zone mt-4">
        {busy && <div className="text-sm text-[color:var(--prism-muted)]">Загрузка…</div>}

        {tab === "audit" && !busy && (
          <div className="admin-panel-surface mb-4 grid grid-cols-1 gap-3 p-3 md:grid-cols-5">
            <input
              type="text"
              placeholder="Действие (action)"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            />
            {/* Sprint 10.4: filter по entity */}
            <input
              type="text"
              placeholder="Entity (users/exercises/ai...)"
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
          <div className="admin-panel-surface prism-scroll overflow-x-auto">
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
            <div className="admin-panel-surface prism-scroll overflow-x-auto">
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

        {tab === "realtime" && !busy && <RealtimeTab state={realtimeState} snapshot={realtimeSnapshot} />}
      </section>
    </div></div></section></main>
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
    <button onClick={onClick} className={`console-pill ${active ? "console-pill-active" : ""}`}>
      {children}
    </button>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/50 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
    </div>
  );
}

function InvitesTab({
  invites,
  loading,
  creating,
  copiedCode,
  role,
  note,
  expiresInDays,
  maxUses,
  onRoleChange,
  onNoteChange,
  onExpiresChange,
  onMaxUsesChange,
  onCreate,
  onCopy,
  onDelete,
}: {
  invites: Invite[];
  loading: boolean;
  creating: boolean;
  copiedCode: string | null;
  role: "student" | "parent" | "teacher";
  note: string;
  expiresInDays: string;
  maxUses: number;
  onRoleChange: (role: "student" | "parent" | "teacher") => void;
  onNoteChange: (note: string) => void;
  onExpiresChange: (value: string) => void;
  onMaxUsesChange: (value: number) => void;
  onCreate: (event: React.FormEvent) => void;
  onCopy: (code: string) => void;
  onDelete: (code: string) => void;
}) {
  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-5">
        <div className="prism-kicker">Invite codes</div>
        <h1 className="mt-2 text-3xl font-black tracking-[-0.04em] text-[color:var(--prism-ink)]">Управление invite-кодами</h1>
        <p className="mt-2 text-sm leading-6 text-[color:var(--prism-muted)]">Создавайте invite codes для друзей/одноклассников Кирилла. Codes можно использовать при регистрации (/register?code=...).</p>
      </section>
      {copiedCode && <div className="rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-3 text-sm font-bold text-[color:var(--prism-ink)]">✓ Code {copiedCode} скопирован в clipboard</div>}
      <section className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-6">
        <h2 className="mb-4 text-lg font-semibold text-[color:var(--prism-ink)]">Создать invite</h2>
        <form onSubmit={onCreate} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="grid gap-1 text-sm font-medium text-[color:var(--prism-muted)]">Роль
              <select value={role} onChange={(e) => onRoleChange(e.target.value as "student" | "parent" | "teacher")} className="prism-input text-sm">
                <option value="student">Student</option><option value="parent">Parent</option><option value="teacher">Teacher</option>
              </select>
            </label>
            <label className="grid gap-1 text-sm font-medium text-[color:var(--prism-muted)]">Max uses
              <input type="number" min="1" max="100" value={maxUses} onChange={(e) => onMaxUsesChange(parseInt(e.target.value) || 1)} className="prism-input text-sm" />
            </label>
          </div>
          <label className="grid gap-1 text-sm font-medium text-[color:var(--prism-muted)]">Note (опционально)
            <input type="text" value={note} onChange={(e) => onNoteChange(e.target.value)} placeholder="Friend of Kirill" maxLength={255} className="prism-input text-sm" />
          </label>
          <label className="grid gap-1 text-sm font-medium text-[color:var(--prism-muted)]">Истекает через (дней, опционально)
            <input type="number" min="1" max="365" value={expiresInDays} onChange={(e) => onExpiresChange(e.target.value)} placeholder="30" className="prism-input text-sm" />
          </label>
          <button type="submit" disabled={creating} className="prism-action primary w-fit px-6 disabled:opacity-50">{creating ? "Создание..." : "Создать invite"}</button>
        </form>
      </section>
      <section className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-6">
        <h2 className="mb-4 text-lg font-semibold text-[color:var(--prism-ink)]">Существующие invites ({invites.length})</h2>
        {loading ? <p className="text-sm text-[color:var(--prism-muted)]">Загрузка...</p> : invites.length === 0 ? <p className="text-sm text-[color:var(--prism-muted)]">No invites yet.</p> : (
          <div className="prism-scroll overflow-x-auto rounded-2xl border border-[color:var(--prism-line)] bg-black/10 p-1">
            <table className="w-full text-sm text-[color:var(--prism-ink)]">
              <thead className="border-b border-[color:var(--prism-line)] text-left text-[color:var(--prism-muted)]"><tr><th className="py-2 pr-4">Code</th><th className="py-2 pr-4">Role</th><th className="py-2 pr-4">Uses</th><th className="py-2 pr-4">Expires</th><th className="py-2 pr-4">Status</th><th /></tr></thead>
              <tbody>{invites.map((invite) => <tr key={invite.code} className="border-b border-[color:var(--prism-line)]"><td className="py-2 pr-4 font-mono text-[color:var(--prism-ink)]">{invite.code}</td><td className="py-2 pr-4 text-[color:var(--prism-muted)]">{invite.role}</td><td className="py-2 pr-4 text-[color:var(--prism-muted)]">{invite.uses_count} / {invite.max_uses}</td><td className="py-2 pr-4 text-[color:var(--prism-muted)]">{invite.expires_at ? new Date(invite.expires_at).toLocaleDateString("ru-RU") : "∞"}</td><td className="py-2 pr-4">{invite.is_valid ? <span className="text-[color:var(--prism-green)]">✓ valid</span> : <span className="text-rose-200">✗ {invite.is_expired ? "expired" : "used"}</span>}</td><td className="py-2 pr-4 text-right"><button onClick={() => onCopy(invite.code)} className="console-pill mr-3 min-h-0 px-3 py-1 text-xs">Copy</button>{invite.uses_count === 0 && <button onClick={() => onDelete(invite.code)} className="console-pill min-h-0 px-3 py-1 text-xs hover-danger">Delete</button>}</td></tr>)}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function RealtimeTab({ state, snapshot }: { state: AdminWSState; snapshot: AdminSnapshot | null }) {
  return (
    <div>
      <section className="border-b border-[color:var(--prism-line)] pb-5">
        <h1 className="mt-1 text-2xl font-bold">Real-time метрики</h1>
        <ConnectionStatus state={state} />
      </section>
      <p className="mt-3 text-sm leading-6 text-[color:var(--prism-muted)]">
        Метрики — это накопительные счётчики с момента последнего старта backend, а не значения “за минуту”.
      </p>
      {snapshot === null ? <p className="mt-6 text-sm text-[color:var(--prism-muted)]">Ожидание первых данных с Prometheus…</p> : (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
          <RealtimeKpi label="AI токены" value={(snapshot.ai_tokens.input || 0) + (snapshot.ai_tokens.output || 0)} sublabel={`Всего токенов AI: input ${snapshot.ai_tokens.input || 0} / output ${snapshot.ai_tokens.output || 0}`} />
          <RealtimeKpi label="AI вызовы" value={Object.values(snapshot.ai_modes).reduce((sum, mode) => sum + (mode?.ok || 0) + (mode?.error || 0), 0)} sublabel={`Всего запросов к AI по ${Object.keys(snapshot.ai_modes).length} режимам`} />
          <RealtimeKpi label="HTTP 5xx" value={snapshot.http_total["5xx"]} sublabel="Ошибки сервера с момента старта backend" danger={snapshot.http_total["5xx"] > 0} />
          <RealtimeKpi label="HTTP 4xx" value={snapshot.http_total["4xx"]} sublabel="Клиентские ошибки: 401/403/404/429" />
          <RealtimeKpi label="HTTP 2xx" value={snapshot.http_total["2xx"]} sublabel="Успешные ответы backend с момента старта" good />
          <RealtimeKpi label="RAM backend" value={snapshot.system.mem_used_pct !== null ? `${Math.round(snapshot.system.mem_used_pct)}%` : "—"} sublabel="Использование памяти внутри backend-контейнера" />
        </div>
      )}
    </div>
  );
}

function ConnectionStatus({ state }: { state: AdminWSState }) {
  const text = { connecting: "Подключение…", open: "● Подключено (real-time)", closed: `Отключено${state.status === "closed" && state.reason ? `: ${state.reason}` : ""}`, error: `Ошибка: ${state.status === "error" ? state.error : ""}` }[state.status];
  return <span className="mt-2 inline-block rounded border border-[color:var(--prism-line)] bg-black/10 px-2 py-1 text-xs font-medium text-[color:var(--prism-muted)]">{text}</span>;
}

function RealtimeKpi({ label, value, sublabel, danger, good }: { label: string; value: string | number; sublabel?: string; danger?: boolean; good?: boolean }) {
  const color = danger ? "text-rose-200" : good ? "text-[color:var(--prism-green)]" : "text-[color:var(--prism-ink)]";
  return <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-4"><div className="text-xs uppercase tracking-wide text-[color:var(--prism-muted)]">{label}</div><div className={`mt-1 text-2xl font-bold ${color}`}>{value}</div>{sublabel && <div className="mt-1 text-xs text-[color:var(--prism-muted)]">{sublabel}</div>}</div>;
}

function ToolsTab() {
  const [busy, setBusy] = useState(false);

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-6">
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
            className="prism-action hover-warn disabled:opacity-50"
          >
            Завершить старые сессии
          </button>
        </div>
      </div>

      {/* Sprint 3.6.3: AI Kill Switch — emergency stop AI для user */}
      <div className="rounded-3xl border border-rose-300/30 bg-[color:var(--prism-panel-solid)]/55 p-6">
        <h3 className="text-lg font-semibold text-[color:var(--prism-ink)]">🚨 AI Kill Switch</h3>
        <p className="mt-1 text-sm text-[color:var(--prism-muted)]">
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
              className="prism-input text-sm"
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
              className="prism-action hover-danger disabled:opacity-50"
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
              className="prism-action disabled:opacity-50"
            >
              Показать список
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}