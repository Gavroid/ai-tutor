"use client";

// Sprint 3.9.6 (Sprint 3.9.6.1 — polish): Управление AI-провайдерами и моделями для предметов.
//
// Дизайн: prism-shell + prism-frame + prism-card + prism-action + admin-panel-surface,
// как у остальных страниц админки (/admin, /admin/users).
//
// 3 секции:
// 1. Провайдеры — список, добавление, удаление, тест, fetch моделей.
// 2. Модели провайдера — поиск (фильтр), чекбоксы is_active.
// 3. Назначения на предметы — primary / fallback выбор.

import { useEffect, useMemo, useState } from "react";
import Header from "@/components/Header";
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

  // Поиск моделей провайдера.
  const [modelSearch, setModelSearch] = useState("");
  const [showOnlyActive, setShowOnlyActive] = useState(false);

  // Subjects + assignments.
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [assignments, setAssignments] = useState<Record<number, SubjectAIAssignment>>({});
  const [allModels, setAllModels] = useState<AIModel[]>([]);

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

      // Загрузим модели всех провайдеров (для dropdown'ов).
      const all: AIModel[] = [];
      for (const prov of p) {
        try {
          const ms = await api.get<AIModel[]>(`/api/v1/admin/ai-providers/${prov.id}/models`);
          all.push(...ms);
        } catch {
          /* ignore */
        }
      }
      setAllModels(all);
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
      if (expanded === id) {
        setExpanded(null);
        setProviderModels([]);
        setTestResult(null);
        setModelSearch("");
        setShowOnlyActive(false);
      }
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
      setModelSearch("");
      setShowOnlyActive(false);
      return;
    }
    setExpanded(id);
    setTestResult(null);
    setModelSearch("");
    setShowOnlyActive(false);
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
      setTestResult({
        ok: false,
        status_code: null,
        error: extractErrorMessage(err),
        latency_ms: null,
        models_count: null,
      });
    } finally {
      setTesting(false);
    }
  }

  async function handleToggleModel(m: AIModel) {
    try {
      await api.patch(`/api/v1/admin/ai-models/${m.id}`, { is_active: !m.is_active });
      const models = await api.get<AIModel[]>(`/api/v1/admin/ai-providers/${m.provider_id}/models`);
      setProviderModels(models);
      await refresh();
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

  // Фильтрация моделей в развёрнутой секции провайдера.
  const filteredProviderModels = useMemo(() => {
    const q = modelSearch.trim().toLowerCase();
    return providerModels.filter((m) => {
      if (showOnlyActive && !m.is_active) return false;
      if (!q) return true;
      return (
        m.model_name.toLowerCase().includes(q) ||
        (m.display_name?.toLowerCase().includes(q) ?? false)
      );
    });
  }, [providerModels, modelSearch, showOnlyActive]);

  // Dropdown'ы: только активные модели со всех провайдеров.
  const activeModelOptions = useMemo(() => {
    const opts: { id: number; label: string; providerName: string; modelName: string }[] = [];
    for (const p of providers) {
      for (const m of allModels) {
        if (m.provider_id === p.id && m.is_active) {
          opts.push({
            id: m.id,
            label: `${p.name} · ${m.model_name}`,
            providerName: p.name,
            modelName: m.model_name,
          });
        }
      }
    }
    return opts;
  }, [providers, allModels]);

  return (
    <main className="prism-shell admin-console min-h-dvh">
      <Header user={null} backHref="/admin" title="AI-провайдеры" />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer p-5 lg:p-10 space-y-6">

            {/* Hero header */}
            <div className="admin-panel-surface prism-card pad">
              <div className="prism-kicker">Sprint 3.9.6 · Мульти-провайдер</div>
              <h1 className="mt-2 text-3xl font-black tracking-[-0.04em] text-[color:var(--prism-ink)]">
                AI-провайдеры и модели для предметов
              </h1>
              <p className="mt-2 text-sm leading-6 text-[color:var(--prism-muted)]">
                Добавьте несколько AI-сервисов (OpenRouter, Groq, OpenAI, Anthropic…).
                Для каждого сервиса получите список моделей, выберите нужные галочками.
                Назначьте модели на предметы: primary используется по умолчанию,
                fallback — автоматически подключается если primary не ответил.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  onClick={() => setFormOpen((v) => !v)}
                  className="prism-action primary"
                >
                  {formOpen ? "Отмена" : "+ Добавить провайдера"}
                </button>
                <a href="/admin" className="prism-action no-underline">
                  ← В админку
                </a>
              </div>
            </div>

            {error && (
              <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 p-3 text-sm text-rose-200">
                {error}
                <button
                  onClick={() => setError(null)}
                  className="ml-2 text-rose-400 hover:text-rose-200"
                >
                  ✕
                </button>
              </div>
            )}

            {/* Add provider form */}
            {formOpen && (
              <div className="admin-panel-surface prism-card pad space-y-4">
                <h2 className="text-lg font-semibold text-[color:var(--prism-ink)]">
                  Новый провайдер
                </h2>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="grid gap-1 text-sm font-medium text-[color:var(--prism-muted)]">
                    Название (для UI)
                    <input
                      className="prism-input text-sm"
                      placeholder="OpenRouter основной"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                    />
                  </label>
                  <label className="grid gap-1 text-sm font-medium text-[color:var(--prism-muted)]">
                    Тип API
                    <select
                      className="prism-input text-sm"
                      value={form.kind}
                      onChange={(e) => setForm({ ...form, kind: e.target.value })}
                    >
                      <option value="openai_compat">OpenAI-compatible (OpenRouter, Groq, OpenAI)</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="google">Google</option>
                    </select>
                  </label>
                  <label className="grid gap-1 text-sm font-medium text-[color:var(--prism-muted)]">
                    Base URL
                    <input
                      className="prism-input text-sm"
                      placeholder="https://openrouter.ai/api/v1"
                      value={form.base_url}
                      onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                    />
                  </label>
                  <label className="grid gap-1 text-sm font-medium text-[color:var(--prism-muted)]">
                    API Key
                    <input
                      type="password"
                      className="prism-input text-sm"
                      placeholder="sk-or-..."
                      value={form.api_key}
                      onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                    />
                  </label>
                  <label className="grid gap-1 text-sm font-medium text-[color:var(--prism-muted)] md:col-span-2">
                    Заметка (опционально)
                    <input
                      className="prism-input text-sm"
                      placeholder="например: основной для физики и математики"
                      value={form.note}
                      onChange={(e) => setForm({ ...form, note: e.target.value })}
                    />
                  </label>
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    onClick={handleCreate}
                    disabled={submitting || !form.name || !form.base_url || !form.api_key}
                    className="prism-action primary disabled:opacity-50"
                  >
                    {submitting ? "Создаю..." : "Создать провайдера"}
                  </button>
                  <button
                    onClick={() => setFormOpen(false)}
                    className="prism-action"
                  >
                    Отмена
                  </button>
                </div>
              </div>
            )}

            {/* Providers list */}
            <div className="admin-panel-surface prism-card pad">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-[color:var(--prism-ink)]">
                  Провайдеры ({providers.length})
                </h2>
              </div>

              {loading ? (
                <div className="text-sm text-[color:var(--prism-muted)] py-6 text-center">
                  Загрузка...
                </div>
              ) : providers.length === 0 ? (
                <div className="text-sm text-[color:var(--prism-muted)] py-6 text-center">
                  Нет ни одного провайдера. Нажми «+ Добавить провайдера» чтобы начать.
                </div>
              ) : (
                <div className="space-y-3">
                  {providers.map((p) => (
                    <div
                      key={p.id}
                      className="rounded-2xl border border-[color:var(--prism-line)] overflow-hidden"
                    >
                      <div className="p-4 flex items-start gap-3 bg-[color:var(--prism-elevated)]/40">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-semibold text-[color:var(--prism-ink)]">
                              {p.name}
                            </h3>
                            {!p.is_active && (
                              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border border-amber-400/40 bg-amber-400/10 text-amber-300 font-bold">
                                выключен
                              </span>
                            )}
                            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border border-[color:var(--prism-line)] text-[color:var(--prism-muted)]">
                              {p.kind}
                            </span>
                            <span className="text-xs text-[color:var(--prism-muted)]">
                              моделей: {p.models_count}
                            </span>
                          </div>
                          <div className="text-sm text-[color:var(--prism-muted)] mt-1 break-all">
                            {p.base_url}
                          </div>
                          <div className="text-xs text-[color:var(--prism-muted)]/80 mt-0.5 font-mono">
                            ключ: {p.api_key_last4}
                            {p.note && <> · {p.note}</>}
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          <button
                            onClick={() => void handleExpand(p.id)}
                            className="prism-action text-xs"
                          >
                            {expanded === p.id ? "Скрыть" : "Модели"}
                          </button>
                          <button
                            onClick={() => void handleTest(p.id)}
                            disabled={testing}
                            className="prism-action text-xs disabled:opacity-50"
                          >
                            {testing ? "..." : "Тест"}
                          </button>
                          <button
                            onClick={() => void handleToggleActive(p)}
                            className="prism-action text-xs"
                          >
                            {p.is_active ? "Выключить" : "Включить"}
                          </button>
                          <button
                            onClick={() => void handleDelete(p.id)}
                            className="prism-action text-xs !border-rose-400/40 !text-rose-300 hover:!bg-rose-500/10"
                          >
                            Удалить
                          </button>
                        </div>
                      </div>

                      {expanded === p.id && (
                        <div className="border-t border-[color:var(--prism-line)] p-4 bg-[color:var(--prism-panel)]/40 space-y-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <button
                              onClick={() => void handleFetch(p.id)}
                              disabled={fetching}
                              className="prism-action primary text-sm disabled:opacity-50"
                            >
                              {fetching ? "Загружаю..." : "⬇ Получить список моделей с провайдера"}
                            </button>
                            <span className="text-xs text-[color:var(--prism-muted)]">
                              GET {p.base_url}/models
                            </span>
                          </div>

                          {testResult && (
                            <div
                              className={`p-3 rounded-2xl text-sm ${testResult.ok
                                  ? "border border-emerald-400/40 bg-emerald-500/10 text-emerald-200"
                                  : "border border-rose-400/40 bg-rose-500/10 text-rose-200"
                                }`}
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

                          {/* Поиск и фильтр моделей */}
                          {providerModels.length > 0 && (
                            <div className="flex flex-wrap items-center gap-2">
                              <input
                                type="search"
                                value={modelSearch}
                                onChange={(e) => setModelSearch(e.target.value)}
                                placeholder={`Поиск среди ${providerModels.length} моделей…`}
                                className="prism-input text-sm flex-1 min-w-[220px]"
                              />
                              <label className="flex items-center gap-2 text-xs text-[color:var(--prism-muted)] cursor-pointer select-none">
                                <input
                                  type="checkbox"
                                  checked={showOnlyActive}
                                  onChange={(e) => setShowOnlyActive(e.target.checked)}
                                  className="rounded"
                                />
                                Только активные
                              </label>
                              <span className="text-xs text-[color:var(--prism-muted)] ml-auto">
                                Показано: {filteredProviderModels.length} / {providerModels.length}
                              </span>
                            </div>
                          )}

                          {/* Список моделей */}
                          <div className="admin-panel-surface rounded-2xl max-h-96 overflow-y-auto">
                            {providerModels.length === 0 ? (
                              <div className="text-sm text-[color:var(--prism-muted)] py-6 text-center">
                                Моделей пока нет. Нажми «Получить список» чтобы дёрнуть /models у провайдера.
                              </div>
                            ) : filteredProviderModels.length === 0 ? (
                              <div className="text-sm text-[color:var(--prism-muted)] py-6 text-center">
                                Ничего не найдено по «{modelSearch}».
                              </div>
                            ) : (
                              <div className="divide-y divide-[color:var(--prism-line)]">
                                {filteredProviderModels.map((m) => (
                                  <div
                                    key={m.id}
                                    className="flex items-center gap-3 px-3 py-2 hover:bg-[color:var(--prism-elevated)]/40 text-sm"
                                  >
                                    <input
                                      type="checkbox"
                                      checked={m.is_active}
                                      onChange={() => void handleToggleModel(m)}
                                      className="rounded"
                                      aria-label={`Активировать ${m.model_name}`}
                                    />
                                    <span
                                      className={`flex-1 font-mono ${m.is_active ? "text-[color:var(--prism-ink)]" : "text-[color:var(--prism-muted)] line-through"}`}
                                    >
                                      {m.model_name}
                                    </span>
                                    <span className="text-xs text-[color:var(--prism-muted)]">
                                      {new Date(m.fetched_at).toLocaleDateString("ru-RU")}
                                    </span>
                                    <button
                                      onClick={() => void handleDeleteModel(m)}
                                      className="text-xs px-2 py-0.5 text-rose-300 hover:bg-rose-500/10 rounded-lg"
                                      aria-label={`Удалить ${m.model_name}`}
                                    >
                                      ✕
                                    </button>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Subject assignments */}
            <div className="admin-panel-surface prism-card pad">
              <div className="prism-kicker">Назначения</div>
              <h2 className="mt-2 text-xl font-black tracking-[-0.03em] text-[color:var(--prism-ink)]">
                Модели для предметов
              </h2>
              <p className="mt-2 text-sm leading-6 text-[color:var(--prism-muted)]">
                Если для предмета настроена <b>primary</b> — будет использоваться она.
                Если primary не ответит — автоматически попробует <b>fallback</b>.
                Если оба не настроены — используется дефолтная модель из ENV.
              </p>

              {subjects.length === 0 ? (
                <div className="text-sm text-[color:var(--prism-muted)] py-6 text-center">
                  Нет предметов.
                </div>
              ) : (
                <div className="mt-4 space-y-2">
                  {subjects.map((subj) => {
                    const a = assignments[subj.id];
                    return (
                      <div
                        key={subj.id}
                        className="grid gap-3 md:grid-cols-[180px_1fr_1fr] items-center px-3 py-2.5 rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel)]/30"
                      >
                        <div className="font-semibold text-[color:var(--prism-ink)] truncate">
                          {subj.name}
                        </div>
                        <label className="grid gap-1 text-xs">
                          <span className="text-[color:var(--prism-muted)] font-bold uppercase tracking-wider">
                            Primary
                          </span>
                          <select
                            className="prism-input text-sm"
                            value={a?.primary?.id ?? ""}
                            onChange={(e) => {
                              const v = e.target.value;
                              void handleAssign(
                                subj.id,
                                "primary",
                                v === "" ? null : Number(v)
                              );
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
                        <label className="grid gap-1 text-xs">
                          <span className="text-[color:var(--prism-muted)] font-bold uppercase tracking-wider">
                            Fallback
                          </span>
                          <select
                            className="prism-input text-sm"
                            value={a?.fallback?.id ?? ""}
                            onChange={(e) => {
                              const v = e.target.value;
                              void handleAssign(
                                subj.id,
                                "fallback",
                                v === "" ? null : Number(v)
                              );
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
            </div>

          </div>
        </div>
      </section>
    </main>
  );
}
