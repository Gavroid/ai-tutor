"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { api } from "@/lib/api";
import type { AdminSnapshot, AdminWSState } from "@/lib/admin-ws";

export type Invite = {
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

export function Tab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button onClick={onClick} className={`console-pill ${active ? "console-pill-active" : ""}`}>
      {children}
    </button>
  );
}

export function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/50 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
    </div>
  );
}

export function InvitesTab({
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
  onCreate: (event: FormEvent) => void;
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

function formatSnapshotTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Europe/Moscow" });
}

function realtimeReasonLabel(reason: string): string {
  const labels: Record<string, string> = {
    missing_topic_draft: "Ожидаемо: черновик темы ещё не создан",
    unauthenticated_snapshot_probe: "Ожидаемо: запрос без admin-сессии",
    unexpected_4xx: "Проверить: неожиданный 4xx",
    server_error: "Проверить: ошибка сервера",
  };
  return labels[reason] || reason;
}

export function RealtimeTab({ state, snapshot, loading, onRefresh }: { state: AdminWSState; snapshot: AdminSnapshot | null; loading: boolean; onRefresh: () => void }) {
  return (
    <div>
      <section className="border-b border-[color:var(--prism-line)] pb-5">
        <h1 className="mt-1 text-2xl font-bold">Real-time метрики</h1>
        <ConnectionStatus state={state} />
      </section>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm leading-6 text-[color:var(--prism-muted)]">
          Метрики — это фиксированный снимок накопительных счётчиков с момента последнего старта backend. Автообновление отключено, чтобы значения не прыгали.
        </p>
        <button type="button" onClick={onRefresh} disabled={loading} className="prism-action shrink-0 px-4 py-2 text-sm disabled:opacity-50">
          {loading ? "Обновляю…" : "Обновить"}
        </button>
      </div>
      {snapshot === null ? <p className="mt-6 text-sm text-[color:var(--prism-muted)]">Ожидание первых данных с Prometheus…</p> : (
        <>
          <div className="mt-4 rounded-2xl border border-[color:var(--prism-line)] bg-black/10 px-3 py-2 text-xs text-[color:var(--prism-muted)]">
            Снимок: {formatSnapshotTime(snapshot.ts)} MSK · значения меняются только после ручного обновления.
          </div>
          <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
            <RealtimeKpi label="DB" value={snapshot.system.db} sublabel="App-level SELECT 1 probe from backend /metrics" good={snapshot.system.db === "ok"} danger={snapshot.system.db !== "ok"} />
            <RealtimeKpi label="Redis" value={snapshot.system.redis} sublabel="App-level Redis ping from backend /metrics" good={snapshot.system.redis === "ok"} danger={snapshot.system.redis !== "ok"} />
            <RealtimeKpi
              label="Backup age"
              value={snapshot.system.backup_latest_age_seconds != null && snapshot.system.backup_latest_age_seconds >= 0 ? `${Math.round(snapshot.system.backup_latest_age_seconds / 3600)}h` : "missing"}
              sublabel="Latest visible backup manifest age; critical above 26h"
              good={snapshot.system.backup_latest_age_seconds != null && snapshot.system.backup_latest_age_seconds >= 0 && snapshot.system.backup_latest_age_seconds <= 93_600}
              danger={snapshot.system.backup_latest_age_seconds == null || snapshot.system.backup_latest_age_seconds < 0 || snapshot.system.backup_latest_age_seconds > 93_600}
            />
            <RealtimeKpi
              label="Upload disk"
              value={snapshot.system.upload_disk_used_percent != null ? `${Math.round(snapshot.system.upload_disk_used_percent)}%` : "—"}
              sublabel="Warning threshold: 80% used"
              good={snapshot.system.upload_disk_used_percent != null && snapshot.system.upload_disk_used_percent <= 80}
              danger={snapshot.system.upload_disk_used_percent != null && snapshot.system.upload_disk_used_percent > 80}
            />
            <RealtimeKpi label="AI токены" value={(snapshot.ai_tokens.input || 0) + (snapshot.ai_tokens.output || 0)} sublabel={`Всего токенов AI: input ${snapshot.ai_tokens.input || 0} / output ${snapshot.ai_tokens.output || 0}`} />
            <RealtimeKpi label="AI вызовы" value={Object.values(snapshot.ai_modes).reduce((sum, mode) => sum + (mode?.ok || 0) + (mode?.error || 0), 0)} sublabel={`Всего запросов к AI по ${Object.keys(snapshot.ai_modes).length} режимам`} />
            <RealtimeKpi label="HTTP 5xx" value={snapshot.http_total["5xx"]} sublabel="Ошибки сервера с момента старта backend" danger={snapshot.http_total["5xx"] > 0} />
            <RealtimeKpi label="HTTP 4xx" value={snapshot.http_total["4xx"]} sublabel="Клиентские ошибки; ниже разделены ожидаемые и требующие проверки" />
            <RealtimeKpi label="HTTP 2xx" value={snapshot.http_total["2xx"]} sublabel="Успешные ответы backend с момента старта" good />
            <RealtimeKpi
              label="RAM backend"
              value={
                snapshot.system.mem_used_pct !== null
                  ? `${Math.round(snapshot.system.mem_used_pct)}%`
                  : snapshot.system.mem_used_mb != null
                    ? `${Math.round(snapshot.system.mem_used_mb)} MiB`
                    : "—"
              }
              sublabel={
                snapshot.system.mem_limit_mb != null
                  ? `Память backend: ${Math.round(snapshot.system.mem_used_mb || 0)} MiB / ${Math.round(snapshot.system.mem_limit_mb)} MiB`
                  : "Фактически занято backend-контейнером; лимит cgroup не задан"
              }
            />
          </div>
          {snapshot.http_breakdown && snapshot.http_breakdown.length > 0 && (
            <section className="mt-6 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-4">
              <h2 className="text-sm font-black uppercase tracking-wide text-[color:var(--prism-muted)]">HTTP 4xx/5xx breakdown</h2>
              <div className="mt-3 grid gap-2">
                {snapshot.http_breakdown.map((item) => (
                  <div key={`${item.path}:${item.status}:${item.kind}`} className="rounded-2xl border border-[color:var(--prism-line)] bg-black/10 p-3 text-xs text-[color:var(--prism-ink)]">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={item.kind === "actionable" ? "text-rose-200" : "text-[color:var(--prism-green)]"}>{item.kind === "actionable" ? "Проверить" : "Ожидаемо"}</span>
                      <span className="font-mono">HTTP {item.status}</span>
                      <span>× {item.count}</span>
                    </div>
                    <div className="mt-1 break-all font-mono text-[color:var(--prism-muted)]">{item.path}</div>
                    <div className="mt-1 text-[color:var(--prism-muted)]">{realtimeReasonLabel(item.reason)}</div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
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

export function ToolsTab() {
  const [busy, setBusy] = useState(false);

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-6">
        <h3 className="text-lg font-semibold text-[color:var(--prism-ink)]">🔧 Диагностика</h3>
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
                if (!window.confirm("Отключить AI для всех пользователей этого user_id? Ученики не смогут получать объяснения и задачи.")) {
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