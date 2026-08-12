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
    <main className="prism-shell admin-console admin-invites-console min-h-dvh py-4 sm:py-7">
      <Header
        user={current}
        backHref="/admin"
        title="Invite codes"
      />
      <section className="prism-frame"><div className="prism-layer mx-auto max-w-5xl p-5 lg:p-10">
        <div className="flex items-center gap-3 mb-6">
          <Link href="/admin" className="text-sky-600 hover:underline text-sm">
            ← К админ-панели
          </Link>
          <h1 className="text-2xl font-bold text-slate-900">Invite codes</h1>
        </div>

        <p className="text-sm text-slate-600 mb-6">
          Создавайте invite codes для друзей/одноклассников Кирилла.
          Codes можно использовать при регистрации (/register?code=...).
        </p>

        {error && (
          <div
            role="alert"
            className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg p-3 mb-4"
            data-testid="invites-error"
          >
            {error}
          </div>
        )}

        {copiedCode && (
          <div
            role="status"
            className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm rounded-lg p-3 mb-4"
            data-testid="copied-code-status"
          >
            ✓ Code {copiedCode} скопирован в clipboard
          </div>
        )}

        {/* Create form */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Создать invite
          </h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="invite-role" className="block text-sm font-medium text-slate-700 mb-1">
                  Роль
                </label>
                <select
                  id="invite-role"
                  value={role}
                  onChange={(e) => setRole(e.target.value as typeof role)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                  data-testid="invite-role-select"
                >
                  <option value="student">Student</option>
                  <option value="parent">Parent</option>
                  <option value="teacher">Teacher</option>
                </select>
              </div>
              <div>
                <label htmlFor="invite-max-uses" className="block text-sm font-medium text-slate-700 mb-1">
                  Max uses
                </label>
                <input
                  id="invite-max-uses"
                  type="number"
                  min="1"
                  max="100"
                  value={maxUses}
                  onChange={(e) => setMaxUses(parseInt(e.target.value) || 1)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                  data-testid="invite-max-uses-input"
                />
              </div>
            </div>

            <div>
              <label htmlFor="invite-note" className="block text-sm font-medium text-slate-700 mb-1">
                Note (опционально)
              </label>
              <input
                id="invite-note"
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Friend of Kirill"
                maxLength={255}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                data-testid="invite-note-input"
              />
            </div>

            <div>
              <label htmlFor="invite-expires" className="block text-sm font-medium text-slate-700 mb-1">
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
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                data-testid="invite-expires-input"
              />
            </div>

            <button
              type="submit"
              disabled={creating}
              className="w-full bg-sky-600 text-white rounded-lg px-4 py-2 font-medium hover:bg-sky-700 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-sky-500"
              data-testid="invite-submit-button"
            >
              {creating ? "Создание..." : "Создать invite"}
            </button>
          </form>
        </section>

        {/* List invites */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Существующие invites ({invites.length})
          </h2>
          {loading ? (
            <p className="text-sm text-slate-500">Загрузка...</p>
          ) : invites.length === 0 ? (
            <p className="text-sm text-slate-500">No invites yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="invites-table">
                <thead className="text-left text-slate-500 border-b border-slate-200">
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
                      className="border-b border-slate-100"
                      data-testid={`invite-row-${inv.code}`}
                    >
                      <td className="py-2 pr-4 font-mono text-slate-800">{inv.code}</td>
                      <td className="py-2 pr-4 text-slate-700">{inv.role}</td>
                      <td className="py-2 pr-4 text-slate-700">
                        {inv.uses_count} / {inv.max_uses}
                      </td>
                      <td className="py-2 pr-4 text-slate-700">
                        {inv.expires_at
                          ? new Date(inv.expires_at).toLocaleDateString("ru-RU")
                          : "∞"}
                      </td>
                      <td className="py-2 pr-4">
                        {inv.is_valid ? (
                          <span className="text-emerald-700">✓ valid</span>
                        ) : (
                          <span className="text-rose-700">
                            ✗ {inv.is_expired ? "expired" : "used"}
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-4 text-right">
                        <button
                          onClick={() => copyToClipboard(inv.code)}
                          className="text-sky-600 hover:underline mr-3"
                          data-testid={`copy-${inv.code}`}
                        >
                          Copy
                        </button>
                        {inv.uses_count === 0 && (
                          <button
                            onClick={() => handleDelete(inv.code)}
                            className="text-rose-600 hover:underline"
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
      </div>
    </section>
    </main>
  );
}