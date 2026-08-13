"use client";

/**
 * Sprint 52: Frontend /admin/invites management page.
 *
 * T1D-friendly: простой UI, без сложной логики.
 * - Create invite (role, note, expires_in_days, max_uses)
 * - List existing invites
 * - Delete unused invite
 * - Copy code to clipboard
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import type { User } from "@/types";

interface Invite {
  code: string;
  role: string;
  note: string | null;
  expires_at: string | null;
  max_uses: number;
  uses_count: number;
  created_at: string;
  is_valid: boolean;
  is_expired: boolean;
}

export default function InvitesAdminPage() {
  const [invites, setInvites] = useState<Invite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [current, setCurrent] = useState<User | null>(null);

  // Form state
  const [role, setRole] = useState<"student" | "parent" | "teacher">("student");
  const [note, setNote] = useState("");
  const [expiresInDays, setExpiresInDays] = useState<string>("");
  const [maxUses, setMaxUses] = useState<number>(1);

  useEffect(() => {
    // Fetch current user для Header.
    fetch("/api/v1/auth/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then(setCurrent)
      .catch(() => setCurrent(null));
    loadInvites();
  }, []);

  async function loadInvites() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch("/api/v1/admin/invites?limit=50", {
        credentials: "include",
      });
      if (!r.ok) {
        if (r.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (r.status === 403) {
          setError("Только admin/teacher могут управлять invites");
          return;
        }
        throw new Error(`HTTP ${r.status}`);
      }
      const data = await r.json();
      setInvites(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        role,
        max_uses: maxUses,
      };
      if (note.trim()) body.note = note.trim();
      if (expiresInDays && parseInt(expiresInDays) > 0) {
        body.expires_in_days = parseInt(expiresInDays);
      }

      const r = await fetch("/api/v1/admin/invites", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${r.status}`);
      }
      const data = await r.json();
      setInvites([data, ...invites]);
      // Clear form
      setNote("");
      setExpiresInDays("");
      setMaxUses(1);
      // Auto-copy code
      await navigator.clipboard.writeText(data.code);
      setCopiedCode(data.code);
      setTimeout(() => setCopiedCode(null), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(code: string) {
    if (!confirm(`Удалить invite ${code}?`)) return;
    setError(null);
    try {
      const r = await fetch(`/api/v1/admin/invites/${code}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${r.status}`);
      }
      setInvites(invites.filter((i) => i.code !== code));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  }

  async function copyToClipboard(code: string) {
    await navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  }

  return (
    <main className="prism-shell admin-console admin-invites-console min-h-dvh">
      <Header
        user={current}
        backHref="/subjects"
        title="Админ-панель"
      />
      <section className="py-3 sm:py-5"><div className="prism-frame"><div className="prism-layer p-5 lg:p-10">
        <nav className="flex flex-wrap gap-2">
          <Link href="/admin?tab=audit" className="console-pill">Audit log</Link>
          <Link href="/admin?tab=users" className="console-pill">Пользователи</Link>
          <Link href="/admin?tab=stats" className="console-pill">Статистика</Link>
          <Link href="/admin?tab=tools" className="console-pill">Инструменты</Link>
          <span className="console-pill console-pill-active" data-testid="invites-tab-link">Invites</span>
          <Link href="/admin/realtime" className="console-pill">Realtime</Link>
        </nav>

        <section className="mt-4 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-5">
          <div className="prism-kicker">Invite codes</div>
          <h1 className="mt-2 text-3xl font-black tracking-[-0.04em] text-[color:var(--prism-ink)]">Управление invite-кодами</h1>
          <p className="mt-2 text-sm leading-6 text-[color:var(--prism-muted)]">
            Создавайте invite codes для друзей/одноклассников Кирилла. Codes можно использовать при регистрации (/register?code=...).
          </p>
        </section>

        {error && (
          <div
            role="alert"
            className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-400/10 p-3 text-sm font-bold text-rose-200"
            data-testid="invites-error"
          >
            {error}
          </div>
        )}

        {copiedCode && (
          <div
            role="status"
            className="mt-4 rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-3 text-sm font-bold text-[color:var(--prism-ink)]"
            data-testid="copied-code-status"
          >
            ✓ Code {copiedCode} скопирован в clipboard
          </div>
        )}

        {/* Create form */}
        <section className="mt-6 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-6">
          <h2 className="mb-4 text-lg font-semibold text-[color:var(--prism-ink)]">
            Создать invite
          </h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="invite-role" className="mb-1 block text-sm font-medium text-[color:var(--prism-muted)]">
                  Роль
                </label>
                <select
                  id="invite-role"
                  value={role}
                  onChange={(e) => setRole(e.target.value as typeof role)}
                  className="prism-input text-sm"
                  data-testid="invite-role-select"
                >
                  <option value="student">Student</option>
                  <option value="parent">Parent</option>
                  <option value="teacher">Teacher</option>
                </select>
              </div>
              <div>
                <label htmlFor="invite-max-uses" className="mb-1 block text-sm font-medium text-[color:var(--prism-muted)]">
                  Max uses
                </label>
                <input
                  id="invite-max-uses"
                  type="number"
                  min="1"
                  max="100"
                  value={maxUses}
                  onChange={(e) => setMaxUses(parseInt(e.target.value) || 1)}
                  className="prism-input text-sm"
                  data-testid="invite-max-uses-input"
                />
              </div>
            </div>

            <div>
              <label htmlFor="invite-note" className="mb-1 block text-sm font-medium text-[color:var(--prism-muted)]">
                Note (опционально)
              </label>
              <input
                id="invite-note"
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Friend of Kirill"
                maxLength={255}
                className="prism-input text-sm"
                data-testid="invite-note-input"
              />
            </div>

            <div>
              <label htmlFor="invite-expires" className="mb-1 block text-sm font-medium text-[color:var(--prism-muted)]">
                Истекает через (дней, опционально)
              </label>
              <input
                id="invite-expires"
                type="number"
                min="1"
                max="365"
                value={expiresInDays}
                onChange={(e) => setExpiresInDays(e.target.value)}
                placeholder="30"
                className="prism-input text-sm"
                data-testid="invite-expires-input"
              />
            </div>

            <button
              type="submit"
              disabled={creating}
              className="prism-action primary w-fit px-6 disabled:opacity-50"
              data-testid="invite-submit-button"
            >
              {creating ? "Создание..." : "Создать invite"}
            </button>
          </form>
        </section>

        {/* List invites */}
        <section className="mt-6 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-6">
          <h2 className="mb-4 text-lg font-semibold text-[color:var(--prism-ink)]">
            Существующие invites ({invites.length})
          </h2>
          {loading ? (
            <p className="text-sm text-[color:var(--prism-muted)]">Загрузка...</p>
          ) : invites.length === 0 ? (
            <p className="text-sm text-[color:var(--prism-muted)]">No invites yet.</p>
          ) : (
            <div className="prism-scroll overflow-x-auto rounded-2xl border border-[color:var(--prism-line)] bg-black/10 p-1">
              <table className="w-full text-sm text-[color:var(--prism-ink)]" data-testid="invites-table">
                <thead className="border-b border-[color:var(--prism-line)] text-left text-[color:var(--prism-muted)]">
                  <tr>
                    <th className="py-2 pr-4">Code</th>
                    <th className="py-2 pr-4">Role</th>
                    <th className="py-2 pr-4">Uses</th>
                    <th className="py-2 pr-4">Expires</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2 pr-4"></th>
                  </tr>
                </thead>
                <tbody>
                  {invites.map((inv) => (
                    <tr
                      key={inv.code}
                      className="border-b border-[color:var(--prism-line)]"
                      data-testid={`invite-row-${inv.code}`}
                    >
                      <td className="py-2 pr-4 font-mono text-[color:var(--prism-ink)]">{inv.code}</td>
                      <td className="py-2 pr-4 text-[color:var(--prism-muted)]">{inv.role}</td>
                      <td className="py-2 pr-4 text-[color:var(--prism-muted)]">
                        {inv.uses_count} / {inv.max_uses}
                      </td>
                      <td className="py-2 pr-4 text-[color:var(--prism-muted)]">
                        {inv.expires_at
                          ? new Date(inv.expires_at).toLocaleDateString("ru-RU")
                          : "∞"}
                      </td>
                      <td className="py-2 pr-4">
                        {inv.is_valid ? (
                          <span className="text-[color:var(--prism-green)]">✓ valid</span>
                        ) : (
                          <span className="text-rose-200">
                            ✗ {inv.is_expired ? "expired" : "used"}
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <button
                          onClick={() => copyToClipboard(inv.code)}
                          className="console-pill mr-3 min-h-0 px-3 py-1 text-xs"
                          data-testid={`copy-${inv.code}`}
                        >
                          Copy
                        </button>
                        {inv.uses_count === 0 && (
                          <button
                            onClick={() => handleDelete(inv.code)}
                            className="console-pill min-h-0 px-3 py-1 text-xs hover-danger"
                            data-testid={`delete-${inv.code}`}
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div></div>
    </section>
    </main>
  );
}