"use client";

// Sprint 3.9.6 — Управление AI-провайдерами и моделями для предметов.
//
// 3 секции:
// 1. Провайдеры — список, добавление, редактирование, удаление, тест, fetch моделей.
// 2. Модели провайдера — чекбоксы is_active.
// 3. Назначения на предметы — primary / fallback выбор.

import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";

// ----- Types -----

type AIProvider = {
  id: number;
  name: string;
  kind: string;
  base_url: string;
  api_key_last4: string;
  is_active: boolean;
  note: string | null;
  created_at: string;
  updated_at: string;
  models_count: number;
};

type AIModel = {
  id: number;
  provider_id: number;
  model_name: string;
  display_name: string | null;
  is_active: boolean;
  fetched_at: string;
};

type AITestResult = {
  ok: boolean;
  status_code: number | null;
  error: string | null;
  latency_ms: number | null;
  models_count: number | null;
};

type Subject = {
  id: number;
  code: string;
  name: string;
};

type SubjectAIAssignment = {
  subject_id: number;
  primary: AIModel | null;
  fallback: AIModel | null;
};

// ----- Helpers -----

function extractErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    return (err.body as { detail?: string })?.detail ?? err.message;
  }
  if (err instanceof Error) return err.message;
  return "Неизвестная ошибка";
}

// ----- Main component -----

export default function AIProvidersPage() {
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state for new provider.
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState({
    name: "",
    kind: "openai_compat",
    base_url: "",
    api_key: "",
    note: "",
  });
  const [submitting, setSubmitting] = useState(false);

  // Expanded provider id (для моделей и теста).
  const [expanded, setExpanded] = useState<number | null>(null);
  const [providerModels, setProviderModels] = useState<AIModel[]>([]);
  const [fetching, setFetching] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<AITestResult | null>(null);

  // Subjects + assignments.
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [assignments, setAssignments] = useState<Record<number, SubjectAIAssignment>>({});

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [p, s] = await Promise.all([
        api.get<AIProvider[]>("/api/v1/admin/ai-providers"),
        api.get<Subject[]>("/api/v1/subjects"),
      ]);
      setProviders(p);
      setSubjects(s);
      // Загрузим assignments для всех предметов.
      const aEntries = await Promise.all(
        s.map(async (subj: Subject) => {
          try {
            const a = await api.get<SubjectAIAssignment>(
              `/api/v1/admin/subjects/${subj.id}/ai-assignment`
            );
            return [subj.id, a] as const;
          } catch {
            return [subj.id, { subject_id: subj.id, primary: null, fallback: null }] as const;
          }
        })
      );
      setAssignments(Object.fromEntries(aEntries));
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function handleCreate() {
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/api/v1/admin/ai-providers", form);
      setForm({ name: "", kind: "openai_compat", base_url: "", api_key: "", note: "" });
      setFormOpen(false);
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Удалить провайдера? Все его модели и назначения тоже удалятся.")) return;
    try {
      await api.delete(`/api/v1/admin/ai-providers/${id}`);
      if (expanded === id) setExpanded(null);
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleToggleActive(p: AIProvider) {
    try {
      await api.patch(`/api/v1/admin/ai-providers/${p.id}`, { is_active: !p.is_active });
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleExpand(id: number) {
    if (expanded === id) {
      setExpanded(null);
      setProviderModels([]);
      setTestResult(null);
      return;
    }
    setExpanded(id);
    setTestResult(null);
    try {
      const models = await api.get<AIModel[]>(`/api/v1/admin/ai-providers/${id}/models`);
      setProviderModels(models);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleFetch(providerId: number) {
    setFetching(true);
    setError(null);
    try {
      await api.post(`/api/v1/admin/ai-providers/${providerId}/fetch`, {});
      const models = await api.get<AIModel[]>(`/api/v1/admin/ai-providers/${providerId}/models`);
      setProviderModels(models);
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setFetching(false);
    }
  }

  async function handleTest(providerId: number) {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.post<AITestResult>(
        `/api/v1/admin/ai-providers/${providerId}/test`,
        {}
      );
      setTestResult(res);
    } catch (err) {
      setTestResult({ ok: false, status_code: null, error: extractErrorMessage(err), latency_ms: null, models_count: null });
    } finally {
      setTesting(false);
    }
  }

  async function handleToggleModel(m: AIModel) {
    try {
      await api.patch(`/api/v1/admin/ai-models/${m.id}`, { is_active: !m.is_active });
      const models = await api.get<AIModel[]>(`/api/v1/admin/ai-providers/${m.provider_id}/models`);
      setProviderModels(models);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleDeleteModel(m: AIModel) {
    if (!confirm(`Удалить модель «${m.model_name}»?`)) return;
    try {
      await api.delete(`/api/v1/admin/ai-models/${m.id}`);
      const models = await api.get<AIModel[]>(`/api/v1/admin/ai-providers/${m.provider_id}/models`);
      setProviderModels(models);
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleAssign(subjectId: number, role: "primary" | "fallback", modelId: number | null) {
    try {
      const body: Record<string, number | null> = {};
      if (modelId === null) body[role] = 0;
      else body[role] = modelId;
      const a = await api.put<SubjectAIAssignment>(
        `/api/v1/admin/subjects/${subjectId}/ai-assignment`,
        body
      );
      setAssignments((prev) => ({ ...prev, [subjectId]: a }));
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  // Список активных моделей для dropdown (с provider name).
  const activeModels = useMemo(() => {
    return providers.flatMap((p) =>
      providerModels
        .filter((m) => m.provider_id === p.id && m.is_active)
        .map((m) => ({
          id: m.id,
          label: `${p.name} · ${m.model_name}`,
        }))
    );
  }, [providers, providerModels]);

  // Общий список моделей для dropdown (даже если не expanded — из всех провайдеров).
  // Соберём модели из всех провайдеров — для этого нужно их подтянуть.
  const [allModels, setAllModels] = useState<AIModel[]>([]);
  useEffect(() => {
    if (providers.length === 0) return;
    void (async () => {
      const all: AIModel[] = [];
      for (const p of providers) {
        try {
          const ms = await api.get<AIModel[]>(`/api/v1/admin/ai-providers/${p.id}/models`);
          all.push(...ms);
        } catch {
          /* ignore */
        }
      }
      setAllModels(all);
    })();
  }, [providers.length]);

  const activeModelOptions = useMemo(() => {
    return providers.flatMap((p) =>
      allModels
        .filter((m) => m.provider_id === p.id && m.is_active)
        .map((m) => ({
          id: m.id,
          label: `${p.name} · ${m.model_name}`,
        }))
    );
  }, [providers, allModels]);

  return (
    <main className="min-h-screen bg-[var(--bg)] text-[var(--fg)] p-6">
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">AI-провайдеры</h1>
        <div className="flex gap-2">
          <a href="/admin" className="px-3 py-1.5 rounded border border-[var(--border)] text-sm hover:bg-[var(--surface)]">
            ← В админку
          </a>
          <button
            onClick={() => setFormOpen((v) => !v)}
            className="px-3 py-1.5 rounded bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90"
          >
            {formOpen ? "Отмена" : "+ Добавить провайдера"}
          </button>
        </div>
      </header>

      {error && (
        <div className="mb-4 p-3 rounded bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-400 hover:text-red-200">
            ✕
          </button>
        </div>
      )}

      {/* Add form */}
      {formOpen && (
        <section className="mb-6 p-4 rounded-lg border border-[var(--border)] bg-[var(--surface)]">
          <h2 className="text-lg font-semibold mb-3">Новый провайдер</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span>Название (для UI)</span>
              <input
                className="px-2 py-1.5 rounded border border-[var(--border)] bg-[var(--bg)]"
                placeholder="OpenRouter основной"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span>Тип API</span>
              <select
                className="px-2 py-1.5 rounded border border-[var(--border)] bg-[var(--bg)]"
                value={form.kind}
                onChange={(e) => setForm({ ...form, kind: e.target.value })}
              >
                <option value="openai_compat">OpenAI-compatible (OpenRouter, Groq, OpenAI)</option>
                <option value="anthropic">Anthropic</option>
                <option value="google">Google</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span>Base URL</span>
              <input
                className="px-2 py-1.5 rounded border border-[var(--border)] bg-[var(--bg)]"
                placeholder="https://openrouter.ai/api/v1"
                value={form.base_url}
                onChange={(e) => setForm({ ...form, base_url: e.target.value })}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span>API Key</span>
              <input
                type="password"
                className="px-2 py-1.5 rounded border border-[var(--border)] bg-[var(--bg)]"
                placeholder="sk-or-..."
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm md:col-span-2">
              <span>Заметка (опционально)</span>
              <input
                className="px-2 py-1.5 rounded border border-[var(--border)] bg-[var(--bg)]"
                placeholder="например: основной для физики и математики"
                value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })}
              />
            </label>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={handleCreate}
              disabled={submitting || !form.name || !form.base_url || !form.api_key}
              className="px-4 py-2 rounded bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50"
            >
              {submitting ? "Создаю..." : "Создать провайдера"}
            </button>
            <button
              onClick={() => setFormOpen(false)}
              className="px-4 py-2 rounded border border-[var(--border)] text-sm hover:bg-[var(--surface)]"
            >
              Отмена
            </button>
          </div>
        </section>
      )}

      {/* Provider list */}
      <section className="mb-8">
        {loading ? (
          <div className="text-center py-8 opacity-60">Загрузка...</div>
        ) : providers.length === 0 ? (
          <div className="text-center py-8 opacity-60">
            Нет ни одного провайдера. Нажми «+ Добавить провайдера» чтобы начать.
          </div>
        ) : (
          <div className="space-y-3">
            {providers.map((p) => (
              <div
                key={p.id}
                className="rounded-lg border border-[var(--border)] bg-[var(--surface)] overflow-hidden"
              >
                <div className="p-4 flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold">{p.name}</h3>
                      {!p.is_active && (
                        <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          выключен
                        </span>
                      )}
                      <span className="text-xs px-2 py-0.5 rounded bg-[var(--bg)] border border-[var(--border)]">
                        {p.kind}
                      </span>
                      <span className="text-xs opacity-70">
                        моделей: {p.models_count}
                      </span>
                    </div>
                    <div className="text-sm opacity-80 mt-1 break-all">{p.base_url}</div>
                    <div className="text-xs opacity-60 mt-0.5">
                      ключ: {p.api_key_last4}
                      {p.note && <> · {p.note}</>}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <button
                      onClick={() => void handleExpand(p.id)}
                      className="text-xs px-2.5 py-1 rounded border border-[var(--border)] hover:bg-[var(--bg)]"
                    >
                      {expanded === p.id ? "Скрыть" : "Модели"}
                    </button>
                    <button
                      onClick={() => void handleTest(p.id)}
                      disabled={testing}
                      className="text-xs px-2.5 py-1 rounded border border-[var(--border)] hover:bg-[var(--bg)] disabled:opacity-50"
                    >
                      {testing ? "..." : "Тест"}
                    </button>
                    <button
                      onClick={() => void handleToggleActive(p)}
                      className="text-xs px-2.5 py-1 rounded border border-[var(--border)] hover:bg-[var(--bg)]"
                    >
                      {p.is_active ? "Выключить" : "Включить"}
                    </button>
                    <button
                      onClick={() => void handleDelete(p.id)}
                      className="text-xs px-2.5 py-1 rounded border border-red-500/40 text-red-300 hover:bg-red-500/10"
                    >
                      Удалить
                    </button>
                  </div>
                </div>

                {expanded === p.id && (
                  <div className="border-t border-[var(--border)] p-4 bg-[var(--bg)]">
                    <div className="flex items-center gap-2 mb-3">
                      <button
                        onClick={() => void handleFetch(p.id)}
                        disabled={fetching}
                        className="text-sm px-3 py-1.5 rounded bg-[var(--accent)] text-white hover:opacity-90 disabled:opacity-50"
                      >
                        {fetching ? "Загружаю..." : "⬇ Получить список моделей с провайдера"}
                      </button>
                      <span className="text-xs opacity-60">
                        Дёргает GET {p.base_url}/models и сохраняет всё новое.
                      </span>
                    </div>

                    {testResult && (
                      <div
                        className={`mb-3 p-2 rounded text-xs ${testResult.ok ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-200" : "bg-red-500/10 border border-red-500/30 text-red-200"}`}
                      >
                        {testResult.ok ? (
                          <>
                            ✅ Соединение OK · статус {testResult.status_code}
                            {testResult.latency_ms != null && ` · ${testResult.latency_ms} мс`}
                            {testResult.models_count != null && ` · ${testResult.models_count} моделей`}
                          </>
                        ) : (
                          <>
                            ❌ {testResult.error}
                            {testResult.status_code != null && ` (HTTP ${testResult.status_code})`}
                          </>
                        )}
                      </div>
                    )}

                    <div className="space-y-1 max-h-80 overflow-y-auto">
                      {providerModels.length === 0 ? (
                        <div className="text-sm opacity-60 py-3 text-center">
                          Моделей пока нет. Нажми «Получить список» чтобы дёрнуть /models у провайдера.
                        </div>
                      ) : (
                        providerModels.map((m) => (
                          <div
                            key={m.id}
                            className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-[var(--surface)] text-sm"
                          >
                            <input
                              type="checkbox"
                              checked={m.is_active}
                              onChange={() => void handleToggleModel(m)}
                              className="rounded"
                            />
                            <span className={`flex-1 ${m.is_active ? "" : "opacity-50"}`}>
                              {m.model_name}
                            </span>
                            <span className="text-xs opacity-50">
                              {new Date(m.fetched_at).toLocaleDateString("ru-RU")}
                            </span>
                            <button
                              onClick={() => void handleDeleteModel(m)}
                              className="text-xs px-1.5 py-0.5 text-red-300 hover:bg-red-500/10 rounded"
                            >
                              ✕
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Subject assignments */}
      <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
        <h2 className="text-lg font-semibold mb-1">Назначения моделей на предметы</h2>
        <p className="text-sm opacity-70 mb-4">
          Если для предмета настроена primary — будет использоваться она. Если primary не ответит —
          автоматически попробует fallback. Если оба не настроены — используется дефолтная модель из ENV.
        </p>
        {subjects.length === 0 ? (
          <div className="text-center py-4 opacity-60">Нет предметов.</div>
        ) : (
          <div className="space-y-3">
            {subjects.map((subj) => {
              const a = assignments[subj.id];
              return (
                <div
                  key={subj.id}
                  className="grid gap-3 md:grid-cols-[200px_1fr_1fr] items-center px-3 py-2 rounded border border-[var(--border)] bg-[var(--bg)]"
                >
                  <div className="font-medium">{subj.name}</div>
                  <label className="flex flex-col gap-1 text-xs">
                    <span className="opacity-70">Primary</span>
                    <select
                      className="px-2 py-1.5 rounded border border-[var(--border)] bg-[var(--surface)] text-sm"
                      value={a?.primary?.id ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        void handleAssign(subj.id, "primary", v === "" ? null : Number(v));
                      }}
                    >
                      <option value="">— не назначено —</option>
                      {activeModelOptions.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-1 text-xs">
                    <span className="opacity-70">Fallback (если primary упадёт)</span>
                    <select
                      className="px-2 py-1.5 rounded border border-[var(--border)] bg-[var(--surface)] text-sm"
                      value={a?.fallback?.id ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        void handleAssign(subj.id, "fallback", v === "" ? null : Number(v));
                      }}
                    >
                      <option value="">— нет —</option>
                      {activeModelOptions.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
